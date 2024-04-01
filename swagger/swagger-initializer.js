window.onload = function() {
  //<editor-fold desc="Changeable Configuration Block">

  const HideCurlPlugin = () => {
    return {
      wrapComponents: {
        curl: () => () => null
      }
    }
  }

  // the following lines will be replaced by docker/configurator, when it runs in a docker-container
  window.ui = SwaggerUIBundle({
    url: "swagger.yaml",
    dom_id: '#swagger-ui',
    deepLinking: true,
    presets: [
      SwaggerUIBundle.presets.apis,
      SwaggerUIStandalonePreset
    ],
    plugins: [
      SwaggerUIBundle.plugins.DownloadUrl,
      HideCurlPlugin
    ],
    layout: "StandaloneLayout"
  });

  //</editor-fold>
};
