FROM maven:3.9.11-eclipse-temurin-25 AS builder

WORKDIR /build

COPY pom.xml ./
COPY omnigate-common ./omnigate-common
COPY omnigate-user ./omnigate-user
COPY omnigate-google ./omnigate-google
COPY omnigate-chatgpt ./omnigate-chatgpt
COPY omnigate-github ./omnigate-github
COPY omnigate-bootstrap ./omnigate-bootstrap

RUN mvn -B -pl omnigate-bootstrap -am -DskipTests package

FROM eclipse-temurin:25-jdk

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV SPRING_PROFILES_ACTIVE=prod
ENV JAVA_OPTS=""

COPY --from=builder /build/omnigate-bootstrap/target/omnigate-bootstrap-*.jar /app/app.jar

EXPOSE 8080

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]
