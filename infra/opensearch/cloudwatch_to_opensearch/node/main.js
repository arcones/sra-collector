// v1.1.2
var https = require('https');
var zlib = require('zlib');
var crypto = require('crypto');

var endpoint = 'search-sracollector-opensearch-bbcrkwlcfb2fjb7psquiefeg2a.eu-central-1.es.amazonaws.com';

var logFailedResponses = true;

exports.handler = function(input, context) {

    var zippedInput = new Buffer.from(input.awslogs.data, 'base64');

    zlib.gunzip(zippedInput, function(error, buffer) {
        if (error) { context.fail(error); return; }

        var awslogsData = JSON.parse(buffer.toString('utf8'));

        var elasticsearchBulkData = transform(awslogsData);

        if (!elasticsearchBulkData) {
            console.log('Received a control message');
            context.succeed('Control message handled successfully');
            return;
        }

        post(elasticsearchBulkData, function(error, success, statusCode, failedItems) {
            console.log('Response: ' + JSON.stringify({
                "statusCode": statusCode
            }));

            if (error) {
                logFailure(error, failedItems);
                context.fail(JSON.stringify(error));
            } else {
                console.log('Success: ' + JSON.stringify(success));
                context.succeed('Success');
            }
        });
    });
};

function transform(payload) {
    var bulkRequestBody = '';

    var indexNameSystem = 'cwl-sra-collector-system';
    var indexNameApp = 'cwl-sra-collector-app';
    var indexNameAccess = 'cwl-sra-collector-access';

    var logOffset = 0

    payload.logEvents.forEach(function(logEvent) {
        var source = buildSource(logEvent.message, logEvent.extractedFields);
        addLogMetadata(payload, source, logOffset)

        if (source.message) {
            bulkRequestBody += addMetaFieldsAndStringify(indexNameApp, logEvent, source)
        } else if (source.type) {
            bulkRequestBody += addMetaFieldsAndStringify(indexNameSystem, logEvent, source)
        } else if (source.httpMethod) {
            source['timestamp'] = new Date().toISOString()

            var full_path = source['path']
            var clean_path_start = full_path.lastIndexOf('/')
            source['path'] = full_path.substring(clean_path_start);

            bulkRequestBody += addMetaFieldsAndStringify(indexNameAccess, logEvent, source)
        } else {
            console.error(`Error: source structure is not expected, please check!!! -> source: ${JSON.stringify(source)}`)
        }

        logOffset++
    });

    return bulkRequestBody;
}

function addLogMetadata(payload, source, logOffset) {
    var full_log_group = payload.logGroup
    var index_of_last_slash = full_log_group.lastIndexOf('/')

    source['log_group'] = full_log_group.substring(index_of_last_slash + 1);
    source['log_offset'] = logOffset
}

function addMetaFieldsAndStringify(indexName, logEvent, source) {
    var action = { "index": {} };
    action.index._index = indexName;
    action.index._id = logEvent.id;

    var bulkRequestBody = '' + [
        JSON.stringify(action),
        JSON.stringify(source),
    ].join('\n') + '\n';

    return bulkRequestBody
}

function buildSource(message, extractedFields) {
    if (extractedFields) {
        var source = {};

        for (var key in extractedFields) {
            if (extractedFields.hasOwnProperty(key) && extractedFields[key]) {
                var value = extractedFields[key];

                if (isNumeric(value)) {
                    source[key] = 1 * value;
                    continue;
                }

                var jsonSubString = extractJson(value);
                if (jsonSubString !== null) {
                    source['$' + key] = JSON.parse(jsonSubString);
                }

                source[key] = value;
            }
        }
        return source;
    }

    var jsonSubString = extractJson(message);
    if (jsonSubString !== null) {
        return JSON.parse(jsonSubString);
    }

    return {};
}

function extractJson(message) {
    var jsonStart = message.indexOf('{');
    if (jsonStart < 0) return null;
    var jsonSubString = message.substring(jsonStart);
    return isValidJson(jsonSubString) ? jsonSubString : null;
}

function isValidJson(message) {
    try {
        JSON.parse(message);
    } catch (e) { return false; }
    return true;
}

function isNumeric(n) {
    return !isNaN(parseFloat(n)) && isFinite(n);
}

function post(body, callback) {
    var requestParams = buildRequest(endpoint, body);

    var request = https.request(requestParams, function(response) {
        var responseBody = '';
        response.on('data', function(chunk) {
            responseBody += chunk;
        });

        response.on('end', function() {
            var info = JSON.parse(responseBody);
            var failedItems;
            var success;
            var error;

            if (response.statusCode >= 200 && response.statusCode < 299) {
                failedItems = info.items.filter(function(x) {
                    return x.index.status >= 300;
                });

                success = {
                    "attemptedItems": info.items.length,
                    "successfulItems": info.items.length - failedItems.length,
                    "failedItems": failedItems.length
                };
            }

            if (response.statusCode !== 200 || info.errors === true) {
                // prevents logging of failed entries, but allows logging
                // of other errors such as access restrictions
                delete info.items;
                error = {
                    statusCode: response.statusCode,
                    responseBody: info
                };
            }

            callback(error, success, response.statusCode, failedItems);
        });
    }).on('error', function(e) {
        callback(e);
    });
    request.end(requestParams.body);
}

function buildRequest(endpoint, body) {
    var endpointParts = endpoint.match(/^([^\.]+)\.?([^\.]*)\.?([^\.]*)\.amazonaws\.com$/);
    var region = endpointParts[2];
    var service = endpointParts[3];
    var datetime = (new Date()).toISOString().replace(/[:\-]|\.\d{3}/g, '');
    var date = datetime.substr(0, 8);
    var kDate = hmac('AWS4' + process.env.AWS_SECRET_ACCESS_KEY, date);
    var kRegion = hmac(kDate, region);
    var kService = hmac(kRegion, service);
    var kSigning = hmac(kService, 'aws4_request');

    var request = {
        host: endpoint,
        method: 'POST',
        path: '/_bulk',
        body: body,
        headers: {
            'Content-Type': 'application/json',
            'Host': endpoint,
            'Content-Length': Buffer.byteLength(body),
            'X-Amz-Security-Token': process.env.AWS_SESSION_TOKEN,
            'X-Amz-Date': datetime
        }
    };

    var canonicalHeaders = Object.keys(request.headers)
        .sort(function(a, b) { return a.toLowerCase() < b.toLowerCase() ? -1 : 1; })
        .map(function(k) { return k.toLowerCase() + ':' + request.headers[k]; })
        .join('\n');

    var signedHeaders = Object.keys(request.headers)
        .map(function(k) { return k.toLowerCase(); })
        .sort()
        .join(';');

    var canonicalString = [
        request.method,
        request.path, '',
        canonicalHeaders, '',
        signedHeaders,
        hash(request.body, 'hex'),
    ].join('\n');

    var credentialString = [ date, region, service, 'aws4_request' ].join('/');

    var stringToSign = [
        'AWS4-HMAC-SHA256',
        datetime,
        credentialString,
        hash(canonicalString, 'hex')
    ] .join('\n');

    request.headers.Authorization = [
        'AWS4-HMAC-SHA256 Credential=' + process.env.AWS_ACCESS_KEY_ID + '/' + credentialString,
        'SignedHeaders=' + signedHeaders,
        'Signature=' + hmac(kSigning, stringToSign, 'hex')
    ].join(', ');

    return request;
}

function hmac(key, str, encoding) {
    return crypto.createHmac('sha256', key).update(str, 'utf8').digest(encoding);
}

function hash(str, encoding) {
    return crypto.createHash('sha256').update(str, 'utf8').digest(encoding);
}

function logFailure(error, failedItems) {
    if (logFailedResponses) {
        console.error('Error: ' + JSON.stringify(error, null, 2));

        if (failedItems && failedItems.length > 0) {
            console.error("Failed Items: " +
                JSON.stringify(failedItems, null, 2));
        }
    }
}
