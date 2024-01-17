# sra-collector

<p align="center">
  <img width="200" src="https://github.com/arcones/sra-collector/blob/main/bioinformaticsbyflaticon.png?raw=true" alt="SRA Collector Logo by Flaticon"/>
</p>



Collect [NIH NCBI](https://www.ncbi.nlm.nih.gov) **SRA** 🧬 metadata of several **GDS** studies in one search 🔮

Use the API directly 👉 [here](https://arcones.github.io/sra-collector/)

> 📢 **Best Effort Design**
>
> NCBI data is sometimes not consistent, therefore, **sra-collector** implements _best effort_ approach, fetching all possible SRA metadata but not giving any guarantees.
>
> Users will be able to check failure reports of each query.


## Infra Diagram
![alt text](./infra/diagram.png "Infrastructure diagram")

## Database Diagram
![alt text](./db/diagram.png "Database diagram")

## Tech Stack

![Static Badge](https://img.shields.io/badge/AWS-orange?logo=amazonaws)
![Static Badge](https://img.shields.io/badge/Python-blue?logo=python&logoColor=yellow)
![Static Badge](https://img.shields.io/badge/Terraform-lavender?logo=terraform)
![Static Badge](https://img.shields.io/badge/PostgreSQL-yellow?logo=postgresql)
![Static Badge](https://img.shields.io/badge/docker-white?logo=docker)
![Static Badge](https://img.shields.io/badge/git-moccasin?logo=git)
![Static Badge](https://img.shields.io/badge/GHActions-black?logo=githubactions)
![Static Badge](https://img.shields.io/badge/Dependabot-deepskyblue?logo=dependabot)
![Static Badge](https://img.shields.io/badge/Swagger-brightgreen?logo=swagger&logoColor=white)
![Static Badge](https://img.shields.io/badge/OpenAPI-dimgray?logo=openapiinitiative)
![Static Badge](https://img.shields.io/badge/SchemaSpy-cornflowerblue?logo=amazondocumentdb&logoColor=black)
![Static Badge](https://img.shields.io/badge/Flyway-red?logo=flyway)
![Static Badge](https://img.shields.io/badge/opensearch-blue?logo=opensearch)
![Static Badge](https://img.shields.io/badge/Precommit-white?logo=precommit)
![Static Badge](https://img.shields.io/badge/make-indigo?logo=cmake)
![Static Badge](https://img.shields.io/badge/bash-black?logo=gnubash&logoColor=chartreuse)

## Style Patterns
- Cloud Native
- Infrastructure As Code
- Asynchronous Communication
- Fail Fast
- Immutable Infrastructure
- Convention Over Configuration
- Encryption
- Passwords Secure Storage
- Continuous Integration & Deployment
- Git Ops
- Don't Repeat Yourself
