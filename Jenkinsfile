// SportsZone Capstone - End-to-End Jenkins Pipeline
//
// Stages: checkout -> unit tests (all 3 services) -> SonarQube code
// quality analysis + quality gate -> build & push 4 Docker images ->
// deploy to Kubernetes (staging namespace) -> wait for rollout ->
// Selenium E2E tests against the live staging URL -> manual approval
// -> promote to production namespace.
//
// This file expects the following to already exist, all set up in
// earlier phases of the capstone:
//   - A Jenkins agent with Python 3.12, Docker, kubectl, and a Chrome
//     browser (for Selenium) installed.
//   - Jenkins credentials configured (Manage Jenkins > Credentials):
//       'dockerhub-creds'      - username/password for your registry
//       'aws-creds'            - AWS access key/secret for kubectl/EKS
//       'sonarqube-token'      - SonarQube authentication token
//   - A SonarQube server registered in Jenkins under the name
//     'sportszone-sonarqube' (Manage Jenkins > System > SonarQube servers).
//   - A kubeconfig for your EKS cluster available to the agent, or
//     configured via the AWS credentials above.

pipeline {
    agent any

    environment {
        REGISTRY        = "132977459197.dkr.ecr.ca-central-1.amazonaws.com"
        IMAGE_TAG       = "${env.BUILD_NUMBER}"
        STAGING_NS      = "sportszone-staging"
        PROD_NS         = "sportszone-prod"
        STAGING_URL     = "http://REPLACE_WITH_YOUR_ALB_HOSTNAME"   // kubectl get svc web-frontend -n sportszone-staging
        AWS_REGION      = "ca-central-1"
        EKS_CLUSTER     = "sportszone-cluster"
        PATH            = "/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin"
        KUBECTL         = "/usr/bin/kubectl"
        AWS             = "/usr/bin/aws"
        DOCKER          = "/usr/bin/docker"
        PYTHON3         = "/usr/bin/python3"
        SONAR           = "/usr/bin/sonar-scanner"
    }

    parameters {
        booleanParam(name: 'SKIP_DEPLOY', defaultValue: false, description: 'Skip Deploy to Staging and Production stages')
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Unit Tests') {
            parallel {
                stage('team-service') {
                    steps {
                        dir('team-service') {
                            sh '/usr/bin/python3 -m venv .venv'
                            sh '. .venv/bin/activate && pip install -r requirements.txt'
                            sh '. .venv/bin/activate && pytest'
                        }
                    }
                    post {
                        always {
                            junit 'team-service/test-results.xml'
                        }
                    }
                }
                stage('player-service') {
                    steps {
                        dir('player-service') {
                            sh '/usr/bin/python3 -m venv .venv'
                            sh '. .venv/bin/activate && pip install -r requirements.txt'
                            sh '. .venv/bin/activate && pytest'
                        }
                    }
                    post {
                        always {
                            junit 'player-service/test-results.xml'
                        }
                    }
                }
                stage('match-service') {
                    steps {
                        dir('match-service') {
                            sh '/usr/bin/python3 -m venv .venv'
                            sh '. .venv/bin/activate && pip install -r requirements.txt'
                            sh '. .venv/bin/activate && pytest'
                        }
                    }
                    post {
                        always {
                            junit 'match-service/test-results.xml'
                        }
                    }
                }
            }
        }

        stage('Code Quality Analysis (SonarQube)') {
            steps {
                withSonarQubeEnv('sportszone-sonarqube') {
                    sh '/usr/bin/sonar-scanner'
                }
            }
        }

        stage('Quality Gate') {
            steps {
                // Fails the build automatically if SonarQube's configured
                // quality gate (coverage, bugs, vulnerabilities, code
                // smells thresholds) is not met. Pipeline pauses here
                // waiting for SonarQube's webhook callback.
                timeout(time: 10, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Build Docker Images') {
            steps {
                script {
                    def services = ['team-service', 'player-service', 'match-service', 'web-frontend']
                    services.each { svc ->
                        sh "/usr/bin/docker build -t ${REGISTRY}/sportszone-${svc}:${IMAGE_TAG} -t ${REGISTRY}/sportszone-${svc}:latest ./${svc}"
                    }
                }
            }
        }

        stage('Push Docker Images') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-creds']]) {
                    sh "/usr/bin/aws ecr get-login-password --region ${AWS_REGION} | /usr/bin/docker login --username AWS --password-stdin ${REGISTRY}"
                    script {
                        def services = ['team-service', 'player-service', 'match-service', 'web-frontend']
                        services.each { svc ->
                            sh "/usr/bin/docker push ${REGISTRY}/sportszone-${svc}:${IMAGE_TAG}"
                            sh "/usr/bin/docker push ${REGISTRY}/sportszone-${svc}:latest"
                        }
                    }
                }
            }
        }

        stage('Deploy to Staging (Kubernetes)') {
            when { expression { return !params.SKIP_DEPLOY } }
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-creds']]) {
                    sh "/usr/bin/aws eks update-kubeconfig --name ${EKS_CLUSTER} --region ${AWS_REGION}"
                    script {
                        def services = ['team-service', 'player-service', 'match-service', 'web-frontend']
                        services.each { svc ->
                            sh "/usr/bin/kubectl set image deployment/${svc} ${svc}=${REGISTRY}/sportszone-${svc}:${IMAGE_TAG} -n ${STAGING_NS}"
                        }
                    }
                    sh "/usr/bin/kubectl rollout status deployment/web-frontend -n ${STAGING_NS} --timeout=180s"
                    sh "/usr/bin/kubectl rollout status deployment/team-service -n ${STAGING_NS} --timeout=180s"
                    sh "/usr/bin/kubectl rollout status deployment/player-service -n ${STAGING_NS} --timeout=180s"
                    sh "/usr/bin/kubectl rollout status deployment/match-service -n ${STAGING_NS} --timeout=180s"
                }
            }
        }

        stage('Browser End-to-End Tests (Selenium)') {
            when { expression { return !params.SKIP_DEPLOY } }
            steps {
                dir('e2e-tests') {
                    sh '/usr/bin/python3 -m venv .venv'
                    sh '. .venv/bin/activate && pip install -r requirements.txt'
                    sh ". .venv/bin/activate && BASE_URL=${STAGING_URL} pytest --junitxml=e2e-results.xml -v"
                }
            }
            post {
                always {
                    junit 'e2e-tests/e2e-results.xml'
                }
            }
        }

        stage('Approval to Promote') {
            when { expression { return !params.SKIP_DEPLOY } }
            steps {
                // A human checks the staging URL and the test/quality
                // results above before production receives the new build.
                input message: "Staging looks good at ${STAGING_URL}. Promote this build to production?", ok: "Promote"
            }
        }

        stage('Deploy to Production (Kubernetes)') {
            when { expression { return !params.SKIP_DEPLOY } }
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-creds']]) {
                    script {
                        def services = ['team-service', 'player-service', 'match-service', 'web-frontend']
                        services.each { svc ->
                            sh "/usr/bin/kubectl set image deployment/${svc} ${svc}=${REGISTRY}/sportszone-${svc}:${IMAGE_TAG} -n ${PROD_NS}"
                        }
                    }
                    sh "/usr/bin/kubectl rollout status deployment/web-frontend -n ${PROD_NS} --timeout=180s"
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline succeeded: build ${IMAGE_TAG} is live."
        }
        failure {
            echo "Pipeline failed - check the stage above for details. Nothing was promoted to production."
        }
        always {
            sh '/usr/bin/docker logout || true'
        }
    }
}
