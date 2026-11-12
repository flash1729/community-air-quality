# Community Air Quality & Environmental Health Dashboard

## Detailed Project Documentation

**Project category:** Cloud Computing\
**Application type:** Responsive web application\
**Primary deployment target:** AWS or Google Cloud Platform (GCP), using
eligible free-tier services\
**Development approach:** Local-first development followed by four
staged releases (MVP + 3 iterations)\
**Primary data providers:** OpenAQ and Open-Meteo

------------------------------------------------------------------------

# 1. Project Overview

The Community Air Quality & Environmental Health Dashboard is a web
application that helps people understand air quality in their city,
neighbourhood, or locality.

The application collects air-quality observations from monitoring
networks and supplements them with weather and model-based air-quality
information. It processes and stores the data, then presents it through
a dashboard containing AQI summaries, pollutant readings, maps,
historical charts, location comparisons, and general health guidance.

The project is designed around two goals:

1.  **Community value:** Make local environmental information easier to
    understand and use.
2.  **Cloud computing demonstration:** Demonstrate cloud hosting,
    scheduled data ingestion, data processing, persistent storage,
    caching, and monitoring without building an unnecessarily complex
    system.

## 1.1 Problem Statement

Air pollution affects people's daily lives, but environmental
information can be scattered across different sources and difficult to
interpret at a neighbourhood level. Users may not know the latest
available pollution readings around their homes, workplaces, or schools,
how those readings have changed over time, or what the reported AQI
category means.

The proposed system provides a centralized, location-oriented dashboard
that collects air-quality and weather information, processes it, and
presents understandable environmental insights. A cloud-based
architecture supports data collection, storage, processing, and access
as the number of locations and users grows.

## 1.2 Project Objectives

-   Show the latest available air-quality information for supported
    locations.
-   Display pollutant measurements and their units.
-   Calculate India-specific AQI when sufficient valid inputs are
    available.
-   Show monitoring stations on an interactive map.
-   Provide historical charts and locality comparisons.
-   Show weather and model-based forecasts separately from measured
    observations.
-   Provide general AQI-based health guidance.
-   Store collected data so that repeated requests do not always require
    external API calls.
-   Demonstrate cloud deployment and cloud data-processing concepts.
-   Keep the application fully testable on a local machine before cloud
    deployment.

## 1.3 Target Users

  -----------------------------------------------------------------------
  User group                          Main use
  ----------------------------------- -----------------------------------
  Residents                           Check air quality around their
                                      locality.

  Students and parents                Understand environmental conditions
                                      around schools and neighbourhoods.

  Commuters                           Compare conditions around home,
                                      work, or frequently visited areas.

  Community groups                    Observe local pollution trends and
                                      hotspots.

  Students and researchers            Explore historical measurements and
                                      export available data.
  -----------------------------------------------------------------------

**Meaning of "community":** People connected by a geographical area,
such as a neighbourhood, locality, town, or city. The application
focuses on local environmental conditions rather than only one
generalized city-wide AQI value.

------------------------------------------------------------------------

# 2. Product Scope

## 2.1 Main User Journey

1.  A user opens the website.
2.  The user searches for a city or locality.
3.  The application finds available monitoring stations and relevant
    environmental data.
4.  The dashboard displays the latest available AQI and pollutant
    readings.
5.  The user can inspect station locations on a map.
6.  The user can explore historical trends and compare locations.
7.  The user can view weather, forecasts, and general health guidance.

The core dashboard should be usable without registration.

## 2.2 In Scope

-   Location search and selection.
-   Latest available air-quality readings.
-   Pollutant details.
-   AQI calculation and classification where valid.
-   Monitoring-station map.
-   Basic and then expanded historical analytics.
-   Location comparison.
-   Weather and air-quality forecast display.
-   General health guidance.
-   Local data persistence and caching.
-   Scheduled precomputation for popular cities.
-   On-demand retrieval and storage for other cities.
-   Cloud deployment and basic monitoring.

## 2.3 Out of Scope for Initial Releases

-   User authentication and profiles.
-   Email, SMS, or push notifications.
-   Administrator dashboard.
-   Citizen-submitted pollution reports.
-   Machine-learning prediction models.
-   Kubernetes and complex microservices.
-   Multi-cloud deployment.
-   Paid external APIs or paid infrastructure.
-   Dedicated native mobile applications.

These may be considered only after the core product is complete and time
and budget permit.

------------------------------------------------------------------------

# 3. Functional Requirements

Priorities: - **P0:** Required for the MVP. - **P1:** Important
follow-up feature. - **P2:** Optional enhancement.

## 3.1 Location and Dashboard

  -----------------------------------------------------------------------
  ID                Feature           Description       Priority
  ----------------- ----------------- ----------------- -----------------
  FR-01             Location search   Search supported  P0
                                      cities and        
                                      localities.       

  FR-02             Location          Select a location P0
                    selection         to view           
                                      environmental     
                                      information.      

  FR-03             Dashboard         Show AQI,         P0
                    overview          available         
                                      pollutants, data  
                                      timestamp, and    
                                      source.           

  FR-04             Data freshness    Indicate whether  P0
                                      readings are      
                                      recent, stale, or 
                                      unavailable.      

  FR-05             Location summary  Summarize         P0
                                      available         
                                      measurements for  
                                      the selected      
                                      location.         
  -----------------------------------------------------------------------

## 3.2 Air Quality and AQI

  -----------------------------------------------------------------------
  ID                Feature           Description       Priority
  ----------------- ----------------- ----------------- -----------------
  FR-06             Pollutant         Display PM2.5,    P0
                    readings          PM10, CO, NO2,    
                                      SO2, and O3 when  
                                      available.        

  FR-07             AQI calculation   Calculate Indian  P0
                                      AQI using CPCB    
                                      methodology when  
                                      inputs are valid. 

  FR-08             AQI category      Display the       P0
                                      applicable AQI    
                                      category.         

  FR-09             Dominant          Identify the      P1
                    pollutant         pollutant with    
                                      the highest valid 
                                      sub-index, where  
                                      determinable.     

  FR-10             Pollutant details Show pollutant    P1
                                      units, source,    
                                      and measurement   
                                      timestamp.        
  -----------------------------------------------------------------------

## 3.3 Map and Location Comparison

  -----------------------------------------------------------------------
  ID                Feature           Description       Priority
  ----------------- ----------------- ----------------- -----------------
  FR-11             Interactive map   Display           P0
                                      monitoring        
                                      stations on a     
                                      map.              

  FR-12             Station details   Show station      P0
                                      name,             
                                      coordinates, and  
                                      available         
                                      readings.         

  FR-13             Location          Compare AQI and   P1
                    comparison        pollutant         
                                      readings across   
                                      selected          
                                      locations.        

  FR-14             Map filtering     Filter stations   P2
                                      by pollutant or   
                                      availability.     
  -----------------------------------------------------------------------

## 3.4 Historical Analytics

  -----------------------------------------------------------------------
  ID                Feature           Description       Priority
  ----------------- ----------------- ----------------- -----------------
  FR-15             Recent history    Show a basic      P0
                                      historical trend  
                                      where data is     
                                      available.        

  FR-16             Date filtering    Filter historical P1
                                      data by date      
                                      range.            

  FR-17             Pollutant trends  Plot individual   P1
                                      pollutant         
                                      readings over     
                                      time.             

  FR-18             Aggregated        Show hourly,      P1
                    summaries         daily, or monthly 
                                      summaries where   
                                      data supports     
                                      them.             

  FR-19             CSV export        Download selected P2
                                      stored            
                                      measurements.     
  -----------------------------------------------------------------------

## 3.5 Weather, Forecasts, and Guidance

  -----------------------------------------------------------------------
  ID                Feature           Description       Priority
  ----------------- ----------------- ----------------- -----------------
  FR-20             Weather summary   Show temperature, P1
                                      humidity, wind,   
                                      and precipitation 
                                      where available.  

  FR-21             Air-quality       Display           P1
                    forecast          model-based       
                                      air-quality       
                                      forecasts.        

  FR-22             Health guidance   Show general      P0
                                      precautions based 
                                      on the applicable 
                                      AQI category.     

  FR-23             Forecast          Clearly           P0
                    labelling         distinguish       
                                      forecasts and     
                                      model estimates   
                                      from station      
                                      observations.     
  -----------------------------------------------------------------------

## 3.6 Data Ingestion and Storage

  -----------------------------------------------------------------------
  ID                Feature           Description       Priority
  ----------------- ----------------- ----------------- -----------------
  FR-24             External API      Retrieve data     P0
                    integration       from OpenAQ and   
                                      Open-Meteo.       

  FR-25             Data              Convert provider  P0
                    normalization     responses into a  
                                      common internal   
                                      format.           

  FR-26             Data validation   Validate units,   P0
                                      timestamps,       
                                      coordinates, and  
                                      values.           

  FR-27             Data persistence  Store retrieved   P0
                                      measurements      
                                      locally and in    
                                      the cloud         
                                      deployment        
                                      database.         

  FR-28             Caching           Reuse recent      P0
                                      results to reduce 
                                      external API      
                                      calls.            

  FR-29             Popular-city      Refresh a         P1
                    precomputation    configured list   
                                      of popular cities 
                                      using scheduled   
                                      jobs.             

  FR-30             On-demand         Fetch and         P1
                    processing        calculate data    
                                      for other cities  
                                      when requested.   

  FR-31             On-demand         Store results for P1
                    persistence       other cities for  
                                      future reuse.     

  FR-32             Retry handling    Retry temporary   P1
                                      provider failures 
                                      with backoff.     
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 4. Non-Functional Requirements

  -----------------------------------------------------------------------
  Category                Requirement             Target / approach
  ----------------------- ----------------------- -----------------------
  Usability               Responsive interface    Support desktop,
                                                  tablet, and mobile
                                                  layouts.

  Performance             API response            Target P95 under 2
                                                  seconds for normal
                                                  cached dashboard
                                                  requests.

  Performance             Dashboard loading       Target under 3 seconds
                                                  under defined test
                                                  conditions.

  Reliability             Provider outage         Show last valid cached
                                                  data with a stale-data
                                                  label.

  Reliability             Data integrity          Do not silently replace
                                                  missing values with
                                                  zero.

  Scalability             Backend                 Keep services stateless
                                                  where practical so
                                                  instances can be
                                                  replicated.

  Scalability             Data                    Index time-series
                                                  queries and retain
                                                  provider metadata.

  Security                Transport               Use HTTPS in cloud
                                                  deployment.

  Security                Secrets                 Keep API keys outside
                                                  source code and
                                                  frontend bundles.

  Security                Input validation        Validate location,
                                                  date-range, and query
                                                  parameters.

  Maintainability         Modularity              Separate UI, API
                                                  routes, provider
                                                  adapters, processing,
                                                  and persistence.

  Portability             Local/cloud parity      Use the same
                                                  application code
                                                  locally and in cloud
                                                  deployment.

  Cost                    Deployment              Target \$0 recurring
                                                  infrastructure cost by
                                                  staying within verified
                                                  free-tier quotas.

  Observability           Monitoring              Track errors, ingestion
                                                  status, API latency,
                                                  and resource usage.
  -----------------------------------------------------------------------

Targets must be measured through tests. They are not automatic
guarantees from a cloud provider.

------------------------------------------------------------------------

# 5. User Interface and Design Language

## 5.1 Design Direction

**Design style:** Clean, modern, data-focused, calm, and accessible.

The interface should feel like a public environmental information
service. It should prioritize readability and clear communication over
decorative elements.

### Visual principles

-   Use a light background with white or lightly tinted content cards.
-   Use dark, high-contrast text for readability.
-   Use green, yellow, orange, red, and deep red only where they
    communicate AQI severity.
-   Use a restrained blue or teal accent for navigation and neutral
    actions.
-   Use consistent spacing, rounded cards, and subtle borders.
-   Avoid excessive gradients, animations, and visual clutter.
-   Use clear labels and units on all charts.
-   Never communicate AQI severity using colour alone; include category
    text and accessible contrast.

### Suggested AQI colour mapping

  CPCB category     AQI range Suggested visual colour
  --------------- ----------- -------------------------
  Good                  0--50 Green
  Satisfactory        51--100 Yellow-green
  Moderate           101--200 Yellow
  Poor               201--300 Orange
  Very Poor          301--400 Red
  Severe             401--500 Deep red

Use the official category names and breakpoints consistently. Ensure
text contrast remains readable.

## 5.2 Main Navigation

Keep navigation small:

-   **Dashboard** --- current overview for the selected location.
-   **History** --- historical charts and comparisons.
-   **About** --- data sources, AQI explanation, and limitations.

For the MVP, these may be sections or tabs within one dashboard rather
than separate complex pages.

## 5.3 Dashboard Layout

Suggested desktop layout:

``` text
+------------------------------------------------------------+
| LOGO       Dashboard   History                    About     |
+------------------------------------------------------------+
| Search city or locality                         [Search]   |
+------------------------------------------------------------+
| Selected location             Last updated: timestamp      |
|                                                            |
| +----------------------+  +-------------------------------+ |
| | CURRENT AQI          |  | HEALTH GUIDANCE               | |
| |  AQI VALUE           |  | Short category-based advice   | |
| |  Category            |  |                               | |
| +----------------------+  +-------------------------------+ |
|                                                            |
| +----------+ +----------+ +----------+ +----------+         |
| | PM2.5    | | PM10     | | NO2      | | O3       |         |
| | Value    | | Value    | | Value    | | Value    |         |
| +----------+ +----------+ +----------+ +----------+         |
|                                                            |
| +-------------------------------+ +----------------------+ |
| | AQI / POLLUTANT TREND          | | WEATHER              | |
| | Historical line chart          | | Temp, wind, humidity | |
| +-------------------------------+ +----------------------+ |
|                                                            |
| +--------------------------------------------------------+ |
| | MAP: Monitoring stations and their latest readings     | |
| +--------------------------------------------------------+ |
|                                                            |
| Data source | Measurement time | Observation / estimate     |
+------------------------------------------------------------+
```

## 5.4 Component Behaviour

### AQI card

-   Show AQI value and category.
-   Show the dominant pollutant when valid.
-   Show measurement or calculation timestamp.
-   Show an unavailable state if AQI cannot be calculated.

### Pollutant cards

-   Show value and unit.
-   Show source and timestamp in details.
-   Use "Unavailable" rather than zero when no reading exists.

### Charts

-   Always label axes and units.
-   Include a legend and time range.
-   Avoid connecting large gaps as if measurements were continuous.
-   Indicate whether data is hourly, daily, observed, or modelled.

### Map

-   Use station markers for actual monitoring locations.
-   Selecting a marker opens station details.
-   Do not imply that every map point is a physical sensor.
-   Any modelled or interpolated layer must be labelled separately.

### Responsive behaviour

-   Desktop: multi-column dashboard.
-   Tablet: two-column cards.
-   Mobile: single-column layout with a compact navigation and map
    height.

## 5.5 Accessibility

-   Use semantic headings and controls.
-   Support keyboard navigation.
-   Provide visible focus states.
-   Use sufficient text contrast.
-   Provide labels or tooltips for chart values.
-   Pair AQI colours with text labels and values.

------------------------------------------------------------------------

# 6. External APIs and Data Sources

The initial product uses two primary API providers.

## 6.1 OpenAQ --- Ground-Level Air-Quality Observations

**Website:** https://openaq.org/\
**API documentation:** https://docs.openaq.org/

Purpose: Retrieve measurements from air-quality monitoring stations.

Potential data: - PM2.5 and PM10. - CO, NO2, SO2, and O3 where
measured. - Monitoring station identifiers and coordinates. - Latest and
historical measurements, subject to provider coverage and endpoint
availability.

Useful API resources (confirm exact parameters and availability in the
current documentation):

  -------------------------------------------------------------------------
  Resource                              Purpose
  ------------------------------------- -----------------------------------
  `GET /v3/locations`                   Discover monitoring locations.

  `GET /v3/locations/{id}`              Retrieve station/location metadata.

  `GET /v3/locations/{id}/latest`       Retrieve latest measurements for a
                                        location.

  `GET /v3/sensors/{id}/measurements`   Retrieve sensor measurements.

  `GET /v3/sensors/{id}/hours`          Retrieve hourly aggregates where
                                        supported.
  -------------------------------------------------------------------------

Implementation notes: - OpenAQ requires an API key. - Keep the key in
backend environment configuration. - Do not call OpenAQ directly from
the browser. - Respect API quotas, pagination, and usage conditions. -
Preserve provider IDs, sensor IDs, units, and timestamps. - Station
availability varies by location and pollutant.

## 6.2 Open-Meteo --- Weather and Model-Based Air Quality

**Air-quality documentation:**
https://open-meteo.com/en/docs/air-quality-api\
**Weather documentation:** https://open-meteo.com/en/docs

Purpose: Supplement station measurements with weather and model-based
air-quality information.

Potential data: - PM2.5, PM10, and other available pollutant model
variables. - Air-quality forecasts. - Temperature and relative
humidity. - Wind speed and direction. - Precipitation.

Useful endpoints:

  -----------------------------------------------------------------------
  Endpoint                            Purpose
  ----------------------------------- -----------------------------------
  `/v1/air-quality`                   Air-quality model and forecast data
                                      for coordinates.

  `/v1/forecast`                      Weather forecast for coordinates.

  `/v1/archive`                       Historical weather, subject to
                                      archive availability.
  -----------------------------------------------------------------------

Implementation notes: - Open-Meteo air-quality values are model-based
and are not equivalent to physical station observations. - Display
forecast/model data separately from station observations. - Check
current terms, attribution, quotas, and commercial-use conditions. -
Cache responses to avoid unnecessary requests.

## 6.3 Supporting Sources

  -----------------------------------------------------------------------
  Source                  Purpose                 Usage
  ----------------------- ----------------------- -----------------------
  CPCB                    Indian AQI methodology  Implement AQI
                          and official            calculation and
                          environmental reference category guidance.
                          information.            

  OpenStreetMap           Geographic map data.    Display maps with
                                                  appropriate attribution
                                                  and tile-use
                                                  compliance.

  WHO                     Air-pollution health    Support general
                          guidance and reference  educational guidance.
                          information.            
  -----------------------------------------------------------------------

Do not assume CPCB's public dashboard provides unrestricted programmatic
API access. Verify access and terms before depending on it as a live
API.

## 6.4 API Responsibility Matrix

  -----------------------------------------------------------------------
  Application feature                 Data source / implementation
  ----------------------------------- -----------------------------------
  Ground-level pollutant readings     OpenAQ

  Station metadata and coordinates    OpenAQ

  Weather information                 Open-Meteo

  Model-based air-quality forecast    Open-Meteo

  Indian AQI calculation              Backend implementation using CPCB
                                      methodology

  AQI category                        Backend implementation using CPCB
                                      breakpoints

  Health guidance                     Internal rule-based content
                                      informed by CPCB/WHO

  Interactive map                     Leaflet + OpenStreetMap

  Historical charts                   Application database

  Location comparison                 Application database and backend

  CSV export                          Backend-generated file
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 7. AQI Calculation and Data Rules

For an India-focused application, calculate Indian AQI using the CPCB
National AQI methodology. Do not treat a US or European AQI index from
another provider as Indian AQI.

The backend should:

1.  Receive pollutant values, units, timestamps, and averaging periods.
2.  Normalize parameter names and units.
3.  Validate values and required averaging periods.
4.  Calculate valid pollutant sub-indices using CPCB breakpoints.
5.  Calculate overall AQI only when CPCB data-availability requirements
    are met.
6.  Assign the corresponding category.
7.  Store the inputs, output, calculation timestamp, and methodology
    version.

The overall AQI is based on the highest valid pollutant sub-index,
subject to CPCB's pollutant availability and validity rules.

### CPCB AQI categories

    AQI range Category
  ----------- --------------
        0--50 Good
      51--100 Satisfactory
     101--200 Moderate
     201--300 Poor
     301--400 Very Poor
     401--500 Severe

**Critical data rule:** If required inputs or averaging periods are
missing, show AQI as unavailable. Do not invent missing pollutant values
or calculate an invalid AQI.

------------------------------------------------------------------------

# 8. Technology Stack

The stack is selected to support quick development, local testing, and a
straightforward cloud deployment.

## 8.1 Frontend

  Technology                Purpose
  ------------------------- -------------------------------------
  Next.js + React           Web application and dashboard.
  TypeScript                Type safety.
  Tailwind CSS              Responsive styling and reusable UI.
  Recharts                  AQI and pollutant charts.
  Leaflet + React-Leaflet   Interactive monitoring-station map.

## 8.2 Backend

  Technology   Purpose
  ------------ ---------------------------------------
  Python       Data processing and AQI calculations.
  FastAPI      REST API and application backend.
  Pydantic     Request and response validation.
  SQLAlchemy   Database access.
  Alembic      Database migrations.
  Pytest       Backend automated tests.

Use Pandas only where it simplifies aggregation or analysis; it is not
necessary for every request.

## 8.3 Database and Storage

  -----------------------------------------------------------------------
  Technology                          Purpose
  ----------------------------------- -----------------------------------
  SQLite                              Fast local MVP database.

  PostgreSQL                          Preferred persistent database for
                                      cloud deployment, if a suitable
                                      free tier is available.

  Local file/cache or database-backed Reuse recent provider responses.
  cache                               

  S3 or Cloud Storage                 Optional raw snapshots and exported
                                      files, if needed.
  -----------------------------------------------------------------------

Keep database access behind a repository/data-access layer so SQLite can
be used locally and PostgreSQL can be adopted for cloud deployment
without rewriting business logic.

## 8.4 Development and Deployment

  Technology              Purpose
  ----------------------- ------------------------------------------------------
  Docker                  Package backend and supporting services.
  Docker Compose          Run the application locally.
  Git + GitHub            Version control and collaboration.
  GitHub Actions          Automated tests and CI/CD.
  Terraform               Optional Infrastructure as Code for cloud resources.
  AWS or GCP monitoring   Application and infrastructure logs/metrics.

------------------------------------------------------------------------

# 9. Cloud Deployment Strategy and Cost Constraint

## 9.1 Cost Objective

The deployment target is **\$0 infrastructure cost**, using services
that are currently eligible for free-tier usage.

This is a target, not a guarantee. Free-tier eligibility, quotas,
account requirements, regions, and pricing can change. Some cloud
providers require a billing account even when resources remain within
free allowances. Budget alerts may notify but may not prevent charges.

Before deployment: - Verify current service pricing and free-tier
limits. - Select one cloud provider, not both. - Avoid paid services and
always-on resources. - Set budget and usage alerts where available. -
Monitor outbound bandwidth, storage, requests, and logs. - Delete unused
resources. - Obtain team approval before enabling any service that may
incur charges.

## 9.2 AWS Service Options

  -----------------------------------------------------------------------
  Need                                Possible AWS service
  ----------------------------------- -----------------------------------
  Container hosting                   ECS/Fargate or another currently
                                      eligible hosting option

  Database                            RDS PostgreSQL only if a suitable
                                      free allowance is available;
                                      otherwise evaluate an eligible
                                      alternative

  Scheduled jobs                      EventBridge Scheduler or an
                                      eligible scheduled execution option

  Object storage                      S3 within eligible usage

  Logs and metrics                    CloudWatch within eligible usage

  Secrets                             Secrets Manager or another secure
                                      configuration option
  -----------------------------------------------------------------------

Do not assume that ECS Fargate, RDS, load balancers, NAT gateways, or
Secrets Manager will be free for the project's account and region.
Verify before selecting them.

## 9.3 GCP Service Options

  -----------------------------------------------------------------------
  Need                                Possible GCP service
  ----------------------------------- -----------------------------------
  Backend hosting                     Cloud Run within eligible usage

  Database                            Cloud SQL only if a suitable free
                                      allowance is available; otherwise
                                      evaluate an eligible alternative

  Scheduled jobs                      Cloud Scheduler or another eligible
                                      scheduled execution option

  Object storage                      Cloud Storage within eligible usage

  Logs and metrics                    Cloud Logging and Cloud Monitoring
                                      within eligible usage

  Secrets                             Secret Manager, after checking
                                      pricing and quotas
  -----------------------------------------------------------------------

Do not assume Cloud SQL, Cloud Scheduler, storage, or logging will be
free for the project's account and region. Verify current terms.

## 9.4 Recommended Deployment Principles

-   Develop and test locally first.
-   Choose AWS or GCP only after checking student credits and free-tier
    quotas.
-   Keep the backend stateless where practical.
-   Use a persistent database; do not rely on container-local storage in
    production.
-   Keep provider keys on the server.
-   Do not add queues, load balancers, or multiple services unless
    required and affordable.
-   Keep cloud-specific configuration separate from application business
    logic.

------------------------------------------------------------------------

# 10. Data Collection and Hybrid Processing Strategy

The application should not schedule data collection for every possible
city. It should use two paths.

## 10.1 Popular Cities: Scheduled Precomputation

Maintain a small configurable list of popular cities, initially around
5--10.

A scheduled job should: 1. Read the configured popular-city list. 2.
Fetch relevant station and weather information. 3. Validate and
normalize provider responses. 4. Calculate AQI where CPCB inputs are
valid. 5. Save measurements and summaries. 6. Record ingestion time and
success/failure status.

The dashboard can then read precomputed data quickly.

## 10.2 Other Cities: On-Demand Processing

When a user searches for a city not in the popular-city list:

1.  Check whether a recent result is already stored.
2.  If fresh data exists, return it.
3.  If no usable recent result exists, call the required provider APIs.
4.  Normalize and validate the response.
5.  Calculate available AQI information.
6.  Store the measurements and derived results.
7.  Return the result with its source and timestamp.

Future users searching for the same location can reuse the stored result
until it expires.

## 10.3 Cache and Freshness Rules

-   Use configurable expiry periods based on provider update frequency
    and data type.
-   Store both measurement time and fetch time.
-   Do not label cached data as live.
-   If a provider fails, return cached data only with a clear stale-data
    warning.
-   Avoid repeated API calls for identical location and time-window
    requests.
-   Use a unique key based on provider, station/sensor, parameter, and
    measurement timestamp to help prevent duplicates.

## 10.4 Logical Data Flow

``` text
POPULAR CITY
Scheduled job
    -> Fetch provider data
    -> Validate and normalize
    -> Calculate valid AQI
    -> Store measurements and summaries
    -> Dashboard reads stored results

OTHER CITY
User searches for city
    -> Check database/cache
    -> Fresh result? Return it
    -> Otherwise fetch required provider data
    -> Validate and normalize
    -> Calculate available AQI
    -> Store result for future use
    -> Return result with source and timestamp
```

------------------------------------------------------------------------

# 11. Proposed System Architecture

Keep the initial architecture modular, not microservice-heavy.

``` text
                 EXTERNAL PROVIDERS
             +-------------------------+
             | OpenAQ                  |
             | Open-Meteo              |
             +------------+------------+
                          |
                          v
                 PROVIDER ADAPTERS
                          |
                          v
                NORMALIZATION LAYER
             +-------------------------+
             | Validate values         |
             | Normalize units         |
             | Preserve source/time    |
             | Deduplicate             |
             +------------+------------+
                          |
                          v
                 PROCESSING LAYER
             +-------------------------+
             | CPCB AQI calculation    |
             | Aggregation             |
             | Health category rules   |
             +------------+------------+
                          |
                          v
                  DATA ACCESS LAYER
                          |
                          v
                 DATABASE + CACHE
                          |
                          v
                    FASTAPI
                    BACKEND
                          |
                          v
                  NEXT.JS FRONTEND
                          |
                          v
                 COMMUNITY DASHBOARD

       SCHEDULED JOB: popular cities only
       ON-DEMAND FLOW: other cities
```

### Local and cloud parity

The same frontend, backend, provider adapters, and business logic must
run locally and in the cloud. Only environment configuration and
infrastructure-specific services should differ.

------------------------------------------------------------------------

# 12. Database Design

Use a small relational schema. Avoid overengineering the database in the
MVP.

  -------------------------------------------------------------------------
  Table                   Key fields                Purpose
  ----------------------- ------------------------- -----------------------
  `locations`             id, name, city, country,  Supported cities and
                          latitude, longitude       localities.

  `stations`              id, provider,             Monitoring stations.
                          external_id, name,        
                          latitude, longitude       

  `sensors`               id, station_id,           Station pollutant
                          parameter, unit           sensors.

  `measurements`          id, sensor_id, value,     Observed measurements.
                          unit, measured_at,        
                          fetched_at, source        

  `aqi_records`           id,                       Derived AQI.
                          station_id/location_id,   
                          aqi, category,            
                          dominant_pollutant,       
                          calculated_at             

  `weather_records`       id, location_id, values,  Weather information.
                          recorded_at, source       

  `forecasts`             id, location_id,          Model-based forecasts.
                          parameter, value,         
                          forecast_for, fetched_at, 
                          source                    

  `ingestion_runs`        id, provider,             Job tracking.
                          location_id, started_at,  
                          completed_at, status,     
                          error                     

  `cache_entries`         cache_key,                Cached provider
                          payload/reference,        results, if
                          fetched_at, expires_at    database-backed caching
                                                    is used.
  -------------------------------------------------------------------------

### Data rules

-   Store timestamps in UTC.
-   Preserve provider and external station/sensor identifiers.
-   Store units explicitly.
-   Separate observations from forecasts.
-   Index station/sensor IDs and measurement timestamps.
-   Do not store missing measurements as zero.
-   Add partitioning only if the measurements table grows enough to
    justify it.

------------------------------------------------------------------------

# 13. Backend API Design

These are application endpoints implemented by the project. They are not
the external OpenAQ or Open-Meteo endpoints.

  --------------------------------------------------------------------------------------
  Method                  Endpoint                               Purpose
  ----------------------- -------------------------------------- -----------------------
  GET                     `/api/v1/locations`                    Search supported
                                                                 locations.

  GET                     `/api/v1/locations/{id}/overview`      Get location dashboard
                                                                 summary.

  GET                     `/api/v1/locations/{id}/stations`      List monitoring
                                                                 stations.

  GET                     `/api/v1/stations/{id}`                Get station details.

  GET                     `/api/v1/stations/{id}/measurements`   Get pollutant readings.

  GET                     `/api/v1/locations/{id}/aqi`           Get calculated AQI.

  GET                     `/api/v1/locations/{id}/history`       Get historical data.

  GET                     `/api/v1/locations/{id}/weather`       Get weather data.

  GET                     `/api/v1/locations/{id}/forecast`      Get model forecast.

  GET                     `/api/v1/compare`                      Compare selected
                                                                 locations.

  GET                     `/api/v1/locations/{id}/export`        Export available data
                                                                 as CSV.

  GET                     `/api/v1/health`                       Application health
                                                                 check.
  --------------------------------------------------------------------------------------

Use pagination and reasonable date-range limits. Validate all query
parameters.

------------------------------------------------------------------------

# 14. Iterative Implementation Plan --- Waterfall-Inspired

The project will use a staged, waterfall-inspired process. Each stage
has defined activities, deliverables, and an acceptance gate. Feedback
from testing can be used to correct the current stage before proceeding.

The four product releases are **MVP + 3 iterations**. Each release
should remain usable.

## Stage 1 --- MVP: Core Dashboard

**Objective:** Deliver the smallest useful end-to-end application.

### Requirements

-   Location search and selection.
-   Latest available AQI and pollutant readings.
-   AQI category and short health advisory.
-   Source and measurement timestamp.
-   Basic monitoring-station map.
-   Simple recent-history chart where data is available.

### Technical work

-   Create Next.js frontend.
-   Create FastAPI backend.
-   Integrate OpenAQ.
-   Integrate Open-Meteo weather endpoint.
-   Implement provider adapters and normalized data models.
-   Implement CPCB AQI calculation for valid inputs.
-   Use SQLite for local persistence.
-   Add basic caching and stale-data handling.
-   Run the entire application locally with documented instructions.

### Testing

-   Location search works.
-   Valid readings are displayed with units and timestamps.
-   Missing pollutant values are handled correctly.
-   AQI is unavailable when CPCB input requirements are not met.
-   Provider failure does not crash the application.
-   Cached results are visibly marked when stale.
-   Frontend build and backend tests pass.

### Deliverables

-   Working local web application.
-   Frontend and backend source code.
-   SQLite database setup.
-   API integration documentation.
-   Basic test suite.
-   Local setup README.

### Exit gate

Do not move to the next stage until the core user journey works locally
from a clean setup.

## Stage 2 --- Iteration 1: Exploration and Analytics

**Objective:** Make the dashboard more informative.

### Features

-   Historical charts with date filters.
-   Pollutant trend charts.
-   Compare two or more supported locations.
-   Weather details.
-   Model-based air-quality forecast view.
-   CSV export.
-   Improved map station details and filters.

### Technical work

-   Extend the database schema.
-   Add history and comparison backend endpoints.
-   Add aggregation queries.
-   Add forecast response handling.
-   Improve chart and map components.

### Testing

-   Historical filters return correct ranges.
-   Comparisons use comparable pollutants, units, and timestamps.
-   Forecasts are visibly distinguished from observations.
-   CSV exports contain correct timestamps and units.
-   Charts handle missing data and gaps.

### Deliverables

-   Expanded dashboard.
-   Historical analytics.
-   Location comparison.
-   Weather and forecast view.
-   CSV export.

### Exit gate

The user can explore and compare stored environmental data without
relying on a fresh provider call for every chart request.

## Stage 3 --- Iteration 2: Smart Data Collection and Performance

**Objective:** Implement the popular-city precomputation and on-demand
strategy.

### Features

-   Configurable list of 5--10 popular cities.
-   Scheduled refresh for popular cities only.
-   On-demand retrieval for other cities.
-   Persist on-demand results for future reuse.
-   Cache expiry and refresh rules.
-   Retry handling for transient provider errors.
-   Ingestion and cache metrics.

### Technical work

-   Add scheduled job entry point.
-   Add popular-city configuration.
-   Add ingestion-run tracking.
-   Add database indexes and deduplication.
-   Add provider request throttling and backoff.
-   Add cache keys and expiry logic.
-   Keep the scheduled job bounded to configured popular cities.

### Testing

-   Scheduled job refreshes only configured popular cities.
-   Other cities are not periodically fetched.
-   First request for an uncached city fetches and stores data.
-   A subsequent request reuses fresh stored data.
-   Expired data is refreshed on demand.
-   Provider failure returns cached data with a stale warning where
    available.
-   Duplicate ingestion does not create duplicate measurement records.

### Deliverables

-   Scheduled popular-city ingestion.
-   On-demand data flow for other cities.
-   Persistent caching and deduplication.
-   Ingestion status and basic metrics.

### Exit gate

Demonstrate both data paths and verify that repeated requests reduce
external API calls.

## Stage 4 --- Iteration 3: Cloud Deployment and Hardening

**Objective:** Deploy the locally tested application to one cloud
provider within verified free-tier limits.

### Features and technical work

-   Select AWS or GCP after checking current free-tier eligibility.
-   Containerize frontend and backend.
-   Deploy application services.
-   Configure a persistent cloud database if an eligible free option
    exists.
-   Configure scheduled execution for popular-city refresh.
-   Configure environment variables and secret storage.
-   Enable HTTPS.
-   Add CI/CD using GitHub Actions.
-   Add cloud logs, health checks, and basic monitoring.
-   Document backup/export and recovery procedures.

### Testing

-   Repeat core user journeys against the cloud deployment.
-   Run a deployment smoke test.
-   Verify secrets are not exposed to the browser or repository.
-   Verify database persistence after application restart.
-   Verify scheduled ingestion runs as expected.
-   Perform a small load test.
-   Check service usage against free-tier quotas.

### Deliverables

-   Publicly accessible deployed application.
-   Deployment configuration.
-   CI/CD workflow.
-   Monitoring and health checks.
-   Cloud architecture diagram.
-   Deployment and recovery documentation.
-   Cost verification checklist.

### Exit gate

The application is usable in the cloud, the main workflows pass, and all
deployed services remain within the team's verified free-tier allowance.

------------------------------------------------------------------------

# 15. Local Development and Testing Strategy

Local testing is mandatory before cloud deployment.

## 15.1 Local Environment

Recommended local services: - Next.js frontend. - FastAPI backend. -
SQLite database for the MVP. - Optional PostgreSQL Docker service before
migrating to PostgreSQL in the cloud.

Use Docker Compose to make setup repeatable. Keep a `.env.example` file
in the repository and keep real keys in a local `.env` file that is
excluded from Git.

## 15.2 Test Data

Provide: - Mock provider responses. - A small sample dataset. -
Automated tests that do not depend on live external APIs.

This ensures that development and demonstrations continue even if an
external provider is unavailable or rate-limited.

## 15.3 Minimum Local Test Checklist

1.  Search for a supported location.
2.  Retrieve and display available pollutant readings.
3.  Display measurement timestamp and source.
4.  Handle missing pollutants.
5.  Calculate AQI only with valid CPCB inputs.
6.  Display station markers on the map.
7.  Display recent history.
8.  Fetch weather data.
9.  Fetch an uncached location on demand.
10. Store the result and reuse it on a later request.
11. Refresh only configured popular cities in the scheduled job.
12. Show cached data with a stale warning after a simulated provider
    failure.
13. Run automated tests and build the frontend successfully.

------------------------------------------------------------------------

# 16. Testing Strategy

  -----------------------------------------------------------------------
  Test type                           What to verify
  ----------------------------------- -----------------------------------
  Unit tests                          AQI calculation, data
                                      normalization, validation, cache
                                      expiry.

  API tests                           Backend endpoint responses and
                                      error handling.

  Integration tests                   Provider adapters and database
                                      persistence.

  Pipeline tests                      Scheduled jobs, on-demand flow,
                                      retries, and deduplication.

  UI tests                            Search, dashboard cards, charts,
                                      map interactions, responsive
                                      layout.

  Performance tests                   Cached dashboard requests and basic
                                      concurrent traffic.

  Security checks                     Secret handling, input validation,
                                      dependency checks, HTTPS.

  Deployment tests                    Health checks, persistence, CI/CD,
                                      and rollback procedure.
  -----------------------------------------------------------------------

Use fixtures and mock responses for predictable tests. Live API tests
should be limited and separate from the regular automated test suite.

------------------------------------------------------------------------

# 17. Risks and Mitigations

  -----------------------------------------------------------------------
  Risk                                Mitigation
  ----------------------------------- -----------------------------------
  No nearby monitoring station        Show station coverage and explain
                                      when locality-level data is
                                      unavailable.

  External API outage                 Reuse cached data with a stale
                                      warning.

  Different AQI standards             Calculate Indian AQI using CPCB
                                      methodology.

  Missing pollutant values            Show unavailable; do not substitute
                                      zero.

  Model data mistaken for             Label observations, estimates, and
  observations                        forecasts separately.

  API quotas exceeded                 Cache, limit requests, and use
                                      scheduled collection only for
                                      popular cities.

  Free-tier limits change             Verify pricing before deployment
                                      and monitor usage.

  Cloud database is not free          Evaluate eligible alternatives
                                      before selecting the deployment
                                      design.

  Cloud storage is ephemeral          Use persistent storage for
                                      production data.

  Scope grows too large               Keep authentication, notifications,
                                      admin, and ML out of the initial
                                      releases.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 18. Final Recommended Project Configuration

  -----------------------------------------------------------------------
  Area                                Decision
  ----------------------------------- -----------------------------------
  Product                             Community Air Quality &
                                      Environmental Health Dashboard

  Primary users                       Residents and people interested in
                                      local environmental conditions

  Frontend                            Next.js, React, TypeScript,
                                      Tailwind CSS

  Backend                             Python, FastAPI, Pydantic

  Charts                              Recharts

  Maps                                Leaflet, OpenStreetMap

  External air-quality data           OpenAQ

  External weather/forecast data      Open-Meteo

  AQI standard                        CPCB National AQI for India

  Local MVP database                  SQLite

  Cloud database                      Persistent PostgreSQL if an
                                      eligible free option is available

  Local execution                     Docker Compose

  Cloud target                        One of AWS or GCP

  Data strategy                       Scheduled popular-city
                                      precomputation + on-demand
                                      retrieval and persistence for other
                                      cities

  Development model                   Waterfall-inspired staged delivery:
                                      MVP + 3 iterations

  Cost target                         \$0 within verified free-tier
                                      quotas
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 19. Definition of Project Success

The project is successful when:

1.  A user can search for a supported locality and see the latest
    available environmental information.
2.  Pollutant values, units, source, and timestamps are visible.
3.  Indian AQI is calculated only when the required inputs are valid.
4.  Monitoring stations can be explored on a map.
5.  Users can view historical trends and compare supported locations.
6.  Weather and model-based forecasts are clearly separated from station
    observations.
7.  Popular cities are refreshed by a scheduled job.
8.  Other cities are fetched on demand, persisted, and reused later.
9.  The entire application can be run and tested locally.
10. The cloud deployment works within verified free-tier limits.

## Final Summary

Build the product in this order:

**Local MVP → Historical analytics → Hybrid data processing → Free-tier
cloud deployment.**

The most important architectural decision is the hybrid data strategy:
precompute a small set of popular cities on a schedule, while processing
other locations only when requested and storing the results for future
reuse.

The most important delivery decision is to keep the application fully
usable locally before cloud deployment. This reduces cloud cost, makes
testing predictable, and prevents deployment issues from blocking core
development.
