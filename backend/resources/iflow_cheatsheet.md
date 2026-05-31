# CPI IFLOW GENERATOR — TENANT CHEAT SHEET (v4)
# Paste this at the start of any new chat with Claude to get correct iFlows immediately.
# Confirmed from live tenant iFlows (May 2026) + official SAP-docs GitHub (btp-integration-suite).
# Sources: 4 working tenant iFlows + SAP official docs for ALL adapter/step properties.

---

## CONTEXT

I am an SAP Integration Suite (CPI) developer. I need you to generate importable iFlow ZIPs.
Use EXACTLY the versions, formats, and structures below — confirmed working on my tenant.
Do NOT guess versions. Do NOT ask for clarification on versions — use these.

---

## ⚠️ CRITICAL RULES — READ FIRST (every single rule is from a real failed import)

### 1. ZIP PACKAGING
Files MUST be at ZIP root — NO parent folder wrapper.
- CORRECT: `.project`, `metainfo.prop`, `META-INF/MANIFEST.MF`, `src/...`
- WRONG: `MyIFlow/.project`, `MyIFlow/metainfo.prop`

PowerShell zip (no wrapper):
```powershell
$zip = [System.IO.Compression.ZipFile]::Open($dst, 'Create')
Get-ChildItem -Path $src -Recurse -File | ForEach-Object {
    $entry = $_.FullName.Substring($src.Length + 1).Replace('\','/')
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $entry, 'Optimal') | Out-Null
}
$zip.Dispose()
```

### 2. metainfo.prop
ONLY a comment line and description. No bundle keys.
```
#Store metainfo properties
description=Your iFlow description here.
```
NEVER use `bundle.symbolicName=`, `Bundle-SymbolicName=`, or `?metainfo=properties`.

### 3. parameters.propdef
Root element is `<parameters>` with `standalone="no"`, NOT `<parameterDefinitions>`.
```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?><parameters><parameter>
    <key/>
    <name>MY_PARAM</name>
    <type>xsd:string</type>
    <isRequired>true</isRequired>
    <constraint/>
    <description>Description here</description>
    <additionalMetadata/>
  </parameter><param_references/></parameters>
```

### 4. MANIFEST.MF — UTF-8 NO BOM + LF line endings + Import-Package headers REQUIRED
Both UTF-8 no-BOM and LF endings are required. BOM → "valid manifest file" error.
Import-Package + Import-Service headers are REQUIRED (confirmed from 4 working iFlows).
Write with PowerShell: `New-Object System.Text.UTF8Encoding($false)` — NOT `[System.Text.Encoding]::UTF8`.

```
Manifest-Version: 1.0
Bundle-ManifestVersion: 2
Bundle-Name: MyIFlow
Bundle-SymbolicName: MyIFlow
Bundle-Version: 1.0.0
SAP-BundleType: IntegrationFlow
SAP-NodeType: IFLMAP
SAP-RuntimeProfile: iflmap
Import-Package: com.sap.esb.application.services.cxf.interceptor,com.sap
 .esb.security,com.sap.it.op.agent.api,com.sap.it.op.agent.collector.cam
 el,com.sap.it.op.agent.collector.cxf,com.sap.it.op.agent.mpl,javax.jms,
 javax.jws,javax.wsdl,javax.xml.bind.annotation,javax.xml.namespace,java
 x.xml.ws,org.apache.camel;version="2.8",org.apache.camel.builder;versio
 n="2.8",org.apache.camel.builder.xml;version="2.8",org.apache.camel.com
 ponent.cxf,org.apache.camel.model;version="2.8",org.apache.camel.proces
 sor;version="2.8",org.apache.camel.processor.aggregate;version="2.8",or
 g.apache.camel.spring.spi;version="2.8",org.apache.commons.logging,org.
 apache.cxf.binding,org.apache.cxf.binding.soap,org.apache.cxf.binding.s
 oap.spring,org.apache.cxf.bus,org.apache.cxf.bus.resource,org.apache.cx
 f.bus.spring,org.apache.cxf.buslifecycle,org.apache.cxf.catalog,org.apa
 che.cxf.configuration.jsse;version="2.5",org.apache.cxf.configuration.s
 pring,org.apache.cxf.endpoint,org.apache.cxf.headers,org.apache.cxf.int
 erceptor,org.apache.cxf.management.counters;version="2.5",org.apache.cx
 f.message,org.apache.cxf.phase,org.apache.cxf.resource,org.apache.cxf.s
 ervice.factory,org.apache.cxf.service.model,org.apache.cxf.transport,or
 g.apache.cxf.transport.common.gzip,org.apache.cxf.transport.http,org.ap
 ache.cxf.transport.http.policy,org.apache.cxf.workqueue,org.apache.cxf.
 ws.rm.persistence,org.apache.cxf.wsdl11,org.osgi.framework;version="1.6
 .0",org.slf4j;version="1.6",org.springframework.beans.factory.config;ve
 rsion="3.0",com.sap.esb.camel.security.cms,org.apache.camel.spi,com.sap
 .esb.webservice.audit.log,com.sap.esb.camel.endpoint.configurator.api,c
 om.sap.esb.camel.jdbc.idempotency.reorg,javax.sql,org.apache.camel.proc
 essor.idempotent.jdbc,org.osgi.service.blueprint;version="[1.0.0,2.0.0)
 "
Import-Service: com.sap.esb.webservice.audit.log.AuditLogger,com.sap.esb
 .security.KeyManagerFactory;multiple:=false,com.sap.esb.security.TrustM
 anagerFactory;multiple:=false,javax.sql.DataSource;multiple:=false;filt
 er="(dataSourceName=default)",org.apache.cxf.ws.rm.persistence.RMStore;
 multiple:=false,com.sap.esb.camel.security.cms.SignatureSplitter;multip
 le:=false
Origin-Bundle-Name: MyIFlow
Origin-Bundle-SymbolicName: MyIFlow

```
(blank line at end required)

### 5. Participants
- Receiver/Sender systems: `ifl:type="EndpointRecevier"` (SAP typo — single 'i' in Recevier)
- Sender: `ifl:type="EndpointSender"`
- IntegrationProcess participant: `id="Participant_Process_1"` with EMPTY `<bpmn2:extensionElements/>`
- Each system participant MUST have inner `<ifl:property><key>ifl:type</key><value>...</value></ifl:property>`
```xml
<bpmn2:participant id="Participant_Process_1" ifl:type="IntegrationProcess"
    name="Integration Process" processRef="Process_1">
    <bpmn2:extensionElements/>
</bpmn2:participant>
```
NEVER use `ifl:type="System"`. NEVER put ifl:type property inside IntegrationProcess participant extensionElements.

### 6. bpmn2:definitions — NO targetNamespace
CORRECT: `<bpmn2:definitions ... id="Definitions_1">`
WRONG:   `<bpmn2:definitions ... id="Definitions_1" targetNamespace="http://www.sap.com/ifl">`

### 7. Collaboration name = "Default Collaboration" always
CORRECT: `<bpmn2:collaboration id="Collaboration_1" name="Default Collaboration">`
WRONG:   `<bpmn2:collaboration id="Collaboration_1" name="MyIFlowName">`
Add documentation: `<bpmn2:documentation id="Documentation_1" textFormat="text/plain">description</bpmn2:documentation>`

### 8. Collaboration extensionElements — full required property set
`httpSessionHandling` = `onExchange` (NOT `None`).
`cmdVariantUri` = `ctype::IFlowVariant/cname::IFlowConfiguration/version::1.2.4`
```xml
<bpmn2:extensionElements>
    <ifl:property><key>namespaceMapping</key><value/></ifl:property>
    <ifl:property><key>httpSessionHandling</key><value>onExchange</value></ifl:property>
    <ifl:property><key>accessControlMaxAge</key><value/></ifl:property>
    <ifl:property><key>returnExceptionToSender</key><value>false</value></ifl:property>
    <ifl:property><key>log</key><value>All events</value></ifl:property>
    <ifl:property><key>corsEnabled</key><value>false</value></ifl:property>
    <ifl:property><key>exposedHeaders</key><value/></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.2</value></ifl:property>
    <ifl:property><key>allowedHeaderList</key><value/></ifl:property>
    <ifl:property><key>ServerTrace</key><value>false</value></ifl:property>
    <ifl:property><key>allowedOrigins</key><value/></ifl:property>
    <ifl:property><key>accessControlAllowCredentials</key><value>false</value></ifl:property>
    <ifl:property><key>allowedHeaders</key><value/></ifl:property>
    <ifl:property><key>allowedMethods</key><value/></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::IFlowVariant/cname::IFlowConfiguration/version::1.2.4</value></ifl:property>
</bpmn2:extensionElements>
```

### 9. Receiver MessageFlow — sourceRef MUST be ServiceTask (Request Reply)
Adapter config on messageFlow from ServiceTask to Participant.
CORRECT: `<bpmn2:messageFlow sourceRef="ServiceTask_xyz" targetRef="Participant_xyz">`
WRONG:   `<bpmn2:messageFlow sourceRef="EndEvent_xyz" targetRef="Participant_xyz">`
The sourceRef in collaboration AND sourceElement in BPMNEdge MUST point to the SAME element.

### 10. Router (CBR) — use bpmn2:exclusiveGateway, conditions on sequenceFlows
WRONG: `bpmn2:callActivity` with ExclusiveGateway activityType + separate GatewayRoute callActivities.
CORRECT: Real `bpmn2:exclusiveGateway` + conditions via `bpmn2:conditionExpression` on sequenceFlows.
```xml
<bpmn2:exclusiveGateway id="ExclusiveGateway_1" name="Route by X">
    <bpmn2:incoming>SF_in</bpmn2:incoming>
    <bpmn2:outgoing>SF_Branch1</bpmn2:outgoing>
    <bpmn2:outgoing>SF_Branch2</bpmn2:outgoing>
</bpmn2:exclusiveGateway>
<bpmn2:sequenceFlow id="SF_Branch1" name="Branch1"
    sourceRef="ExclusiveGateway_1" targetRef="ServiceTask_1">
    <bpmn2:extensionElements>
        <ifl:property><key>expressionType</key><value>Non-XML</value></ifl:property>
        <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::GatewayRoute/version::1.0.0</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:conditionExpression id="FormalExpression_SF_Branch1"
        xsi:type="bpmn2:tFormalExpression">${property.myProp} = 'value'</bpmn2:conditionExpression>
</bpmn2:sequenceFlow>
```
- `expressionType=Non-XML` for property/header conditions; `expressionType=XML` for XPath conditions.
- BPMNShape for ExclusiveGateway: `height="40.0" width="40.0"` (diamond).

### 11. Exception Subprocess — NO triggeredByEvent attribute
`<bpmn2:subProcess id="SubProcess_Error" name="Exception Subprocess">` — NO `triggeredByEvent="true"`.

### 12. BPMN Diagram — REQUIRED, name="Default Collaboration Diagram"
Without `<bpmndi:BPMNDiagram name="Default Collaboration Diagram">` CPI throws "unable to load".

### 13. Every di:waypoint MUST have xsi:type="dc:Point"
CORRECT: `<di:waypoint x="192.0" xsi:type="dc:Point" y="160.0"/>`
WRONG:   `<di:waypoint x="192.0" y="160.0"/>`

### 14. Every BPMNEdge MUST have sourceElement and targetElement
```xml
<bpmndi:BPMNEdge bpmnElement="SF_1" id="BPMNEdge_SF_1"
    sourceElement="BPMNShape_StartEvent_1" targetElement="BPMNShape_CallActivity_1">
```

### 15. Shape IDs: BPMNShape_<bpmnElement>   Edge IDs: BPMNEdge_<bpmnElement>

### 16. iflw XML style: indented multi-line 4-space indent, NOT minified/single-line.

---

## CONFIRMED VERSIONS — from 4 live tenant iFlows (May 2026)

### Flow Elements
```
IntegrationProcess      ctype::FlowElementVariant/cname::IntegrationProcess/version::1.2.1   ← USE THIS
IntegrationProcess      ctype::FlowElementVariant/cname::IntegrationProcess/version::1.2.0   ← also valid
LocalIntegrationProcess ctype::FlowElementVariant/cname::LocalIntegrationProcess/version::1.1.3
IFlowConfiguration      ctype::IFlowVariant/cname::IFlowConfiguration/version::1.2.4         ← USE THIS
IFlowConfiguration      ctype::IFlowVariant/cname::IFlowConfiguration/version::1.2.3         ← also valid
```

### Flow Steps (all bpmn2:callActivity unless noted)
```
Step Type              activityType                   cmdVariantUri
────────────────────────────────────────────────────────────────────────────────────────────
Groovy Script          Script                         ctype::FlowstepVariant/cname::GroovyScript/version::1.1.2
Content Modifier       Enricher                       ctype::FlowstepVariant/cname::Enricher/version::1.5.3  ← USE THIS
Content Modifier       Enricher                       ctype::FlowstepVariant/cname::Enricher/version::1.5.1  ← also valid
Content Modifier       Enricher                       ctype::FlowstepVariant/cname::Enricher/version::1.6.0  ← also valid
Request Reply          ExternalCall                   ctype::FlowstepVariant/cname::ExternalCall/version::1.0.4
JSON to XML            JsonToXmlConverter             ctype::FlowstepVariant/cname::JsonToXmlConverter/version::1.1.2
XML to JSON            XmlToJsonConverter             ctype::FlowstepVariant/cname::XmlToJsonConverter/version::1.0.8
Message Mapping        Mapping                        ctype::FlowstepVariant/cname::MessageMapping/version::1.3.1
DataStore Write        DBstorage                      ctype::FlowstepVariant/cname::put/version::1.7.1
Router Branch          GatewayRoute (on sequenceFlow) ctype::FlowstepVariant/cname::GatewayRoute/version::1.0.0
General Splitter       Splitter                       ctype::FlowstepVariant/cname::GeneralSplitter/version::1.6.0
Iterating Splitter     Splitter                       ctype::FlowstepVariant/cname::Camel/version::1.5.1
Gather                 Gather                         ctype::FlowstepVariant/cname::Gather/version::1.2.0
Join                   Join                           ctype::FlowstepVariant/cname::Join/version::1.0.0
Sequential Multicast   SequentialMulticast            ctype::FlowstepVariant/cname::SequentialMulticast/version::1.1.0
Content Enricher       contentEnricherWithLookup      ctype::FlowstepVariant/cname::contentEnricherWithLookup/version::1.2.0
Filter                 Filter                         ctype::FlowstepVariant/cname::Filter/version::1.1.0
ZIP Compress           Encoder                        ctype::FlowstepVariant/cname::ZIP Compress/version::1.0.1
Base64 Encode          Encoder                        ctype::FlowstepVariant/cname::Base64 Encode/version::1.0.1
Timer (start)          StartTimerEvent                ctype::FlowstepVariant/cname::intermediatetimer/version::1.3.0
Timer (start newer)    StartTimerEvent                ctype::FlowstepVariant/cname::intermediatetimer/version::1.4.0
Error Subprocess       ErrorEventSubProcessTemplate   ctype::FlowstepVariant/cname::ErrorEventSubProcessTemplate/version::1.1.0 ← USE THIS
Error Subprocess (old) ErrorEventSubProcessTemplate   ctype::FlowstepVariant/cname::ErrorEventSubProcessTemplate/version::1.0.2
Message End Event      (none — bpmn2:endEvent)        ctype::FlowstepVariant/cname::MessageEndEvent/version::1.1.0
Message Start Event    (none — bpmn2:startEvent)      ctype::FlowstepVariant/cname::MessageStartEvent  (no version)
Error End Event        EndErrorEvent                  ctype::FlowstepVariant/cname::ErrorEndEvent  (no version)
Error Start Event      StartErrorEvent                ctype::FlowstepVariant/cname::ErrorStartEvent  (no version)
Local Process End      EndEvent                       ctype::FlowstepVariant/cname::EndEvent  (no version)
Local Process Start    StartEvent                     ctype::FlowstepVariant/cname::StartEvent  (no version)
Process Call           ProcessCallElement             ctype::FlowstepVariant/cname::NonLoopingProcess/version::1.0.3
Loop Process           ProcessCallElement             ctype::FlowstepVariant/cname::LoopingProcess/version::1.3.0
```

### Adapters
```
HTTPS Sender      ctype::AdapterVariant/cname::sap:HTTPS/tp::HTTPS/mp::None/direction::Sender/version::1.5.0   ← USE THIS (confirmed from live tenant)
HTTPS Sender      ctype::AdapterVariant/cname::sap:HTTPS/tp::HTTPS/mp::None/direction::Sender/version::1.5.2   ← also valid
HTTP Receiver     ctype::AdapterVariant/cname::sap:HTTP/tp::HTTP/mp::None/direction::Receiver/version::1.15.0  ← USE THIS (confirmed from live tenant)
HTTP Receiver     ctype::AdapterVariant/cname::sap:HTTP/tp::HTTP/mp::None/direction::Receiver/version::1.17.1  ← also valid
OData Receiver    ctype::AdapterVariant/cname::sap:HCIOData/tp::HTTP/mp::OData V2/direction::Receiver/version::1.24.0  ← USE THIS (confirmed)
OData Receiver    ctype::AdapterVariant/cname::sap:HCIOData/tp::HTTP/mp::OData V2/direction::Receiver/version::1.25.0  ← also valid
OData Receiver    ctype::AdapterVariant/cname::sap:HCIOData/tp::HTTP/mp::OData V2/direction::Receiver/version::1.27.0  ← also valid
ProcessDirect     ctype::AdapterVariant/cname::ProcessDirect/vendor::SAP/tp::Not Applicable/mp::Not Applicable/direction::Receiver/version::1.1.1
SOAP Receiver     ctype::AdapterVariant/cname::sap:SOAP/tp::HTTP/mp::SOAP 1.x/direction::Receiver/version::1.12.3
SFTP Receiver     ctype::AdapterVariant/cname::sap:SFTP/tp::SFTP/mp::File/direction::Receiver/version::1.13.3  ← ✅ CONFIRMED from live tenant (mp::File NOT mp::None)
IDoc Receiver     ctype::AdapterVariant/cname::sap:IDoc/tp::HTTP/mp::IDoc/direction::Receiver/version::1.x.x   ← ⚠️ verify on tenant
Mail Receiver     ctype::AdapterVariant/cname::sap:Mail/tp::SMTP/mp::None/direction::Receiver/version::x.x.x   ← ⚠️ verify on tenant
```

---

## COMPLETE ADAPTER PROPERTY SETS
### (Source: SAP official docs + confirmed live tenant iFlows)

---

### HTTPS Sender (v1.5.0 — ✅ confirmed from live tenant CPI-saved iflw)
**Note: `enableBasicAuthentication=false` must be added to EndpointSender participant (confirmed from CPI-saved):**
```xml
<bpmn2:participant id="Participant_S4" ifl:type="EndpointSender" name="S4 HANA">
    <bpmn2:extensionElements>
        <ifl:property><key>enableBasicAuthentication</key><value>false</value></ifl:property>
        <ifl:property><key>ifl:type</key><value>EndpointSender</value></ifl:property>
    </bpmn2:extensionElements>
</bpmn2:participant>
```
```xml
<key>ComponentType</key><value>HTTPS</value>
<key>ComponentNS</key><value>sap</value>
<key>componentVersion</key><value>1.5</value>
<key>Name</key><value>HTTPS</value>
<key>Description</key><value/>
<key>TransportProtocolVersion</key><value>1.5.0</value>
<key>ComponentSWCVName</key><value>external</value>
<key>ComponentSWCVId</key><value>1.5.0</value>
<key>TransportProtocol</key><value>HTTPS</value>
<key>MessageProtocol</key><value>None</value>
<key>MessageProtocolVersion</key><value>1.5.0</value>
<key>direction</key><value>Sender</value>
<key>system</key><value>SenderSystem</value>
<key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:HTTPS/tp::HTTPS/mp::None/direction::Sender/version::1.5.0</value>
<!-- Connection Tab -->
<key>urlPath</key><value>{{Sender_Endpoint_Path}}</value>           <!-- must start with / -->
<key>xsrfProtection</key><value>{{HTTPS_AEM_CSRF}}</value>          <!-- 1=enabled, 0=disabled, or param ref -->
<key>senderAuthType</key><value>RoleBased</value>                    <!-- RoleBased | ClientCertificate | None -->
<key>userRole</key><value>ESBMessaging.send</value>                  <!-- role or param ref -->
<key>clientCertificates</key><value/>                                <!-- only if senderAuthType=ClientCertificate -->
<!-- Conditions Tab -->
<key>maximumBodySize</key><value>40</value>                          <!-- MB, min 1 -->
```

**Headers set by HTTPS Sender (read-only at runtime):**
- `SapAuthenticatedUserName` — caller username
- `CamelHttpUrl` — full URL without query params
- `CamelHttpQuery` — query string
- `CamelHttpMethod` — GET/POST/PUT/DELETE etc.
- `CamelServletContextPath` — address field path
- `CamelHttpPath` — dynamic path beyond endpoint (when address ends with `*`)

---

### HTTP Receiver (v1.15.0 — ✅ confirmed from live tenant CPI-saved iflw)
**Additional fields confirmed from CPI-saved (were missing before):** `methodSourceExpression`, `httpAddressQuery`, `httpShouldSendBody`, `httpErrorResponseCodes`, `allowedRequestHeaders`, `locationID`
```xml
<key>ComponentType</key><value>HTTP</value>
<key>ComponentNS</key><value>sap</value>
<key>componentVersion</key><value>1.15</value>
<key>Name</key><value>HTTP</value>
<key>Description</key><value/>
<key>TransportProtocolVersion</key><value>1.15.0</value>
<key>ComponentSWCVName</key><value>external</value>
<key>ComponentSWCVId</key><value>1.15.0</value>
<key>TransportProtocol</key><value>HTTP</value>
<key>MessageProtocol</key><value>None</value>
<key>MessageProtocolVersion</key><value>1.15.0</value>
<key>direction</key><value>Receiver</value>
<key>system</key><value>ReceiverSystem</value>
<key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:HTTP/tp::HTTP/mp::None/direction::Receiver/version::1.15.0</value>
<!-- Connection Tab -->
<key>httpAddressWithoutQuery</key><value>{{Receiver_URL}}</value>    <!-- full URL, no query params -->
<key>httpAddressQuery</key><value>{{Receiver_Query}}</value>          <!-- query string (NOT in address) -->
<key>proxyType</key><value>Internet</value>                           <!-- Internet | On-Premise | Manual -->
<key>proxyHost</key><value/>                                          <!-- Manual proxy only -->
<key>proxyPort</key><value/>                                          <!-- Manual proxy only -->
<key>locationID</key><value/>                                         <!-- On-Premise only -->
<key>httpMethod</key><value>POST</value>                              <!-- POST|GET|PUT|DELETE|PATCH|HEAD|TRACE|Dynamic -->
<key>httpShouldSendBody</key><value>false</value>                     <!-- send body on GET/DELETE/HEAD? -->
<key>authenticationMethod</key><value>Basic</value>                   <!-- None|Basic|OAuth2 Client Credentials|Client Certificate|Principal Propagation -->
<key>credentialName</key><value>{{Receiver_Credential}}</value>       <!-- User Credentials alias -->
<key>privateKeyAlias</key><value/>                                    <!-- Client Certificate only -->
<key>httpRequestTimeout</key><value>60000</value>                     <!-- ms, default 60000 -->
<key>streaming</key><value>false</value>                              <!-- disk-based streaming for large payloads -->
<key>throwExceptionOnFailure</key><value>true</value>                 <!-- throw on HTTP error -->
<key>enableMPLAttachments</key><value>true</value>                    <!-- attach error details to MPL -->
<key>retryOnConnectionFailure</key><value>false</value>
<key>retryIteration</key><value>1</value>                             <!-- max 3 -->
<key>retryInterval</key><value>5</value>                              <!-- seconds, max 60 -->
<key>httpErrorResponseCodes</key><value/>                             <!-- comma-separated codes to retry -->
<!-- Header Details -->
<key>allowedRequestHeaders</key><value>{{Request_Headers}}</value>    <!-- pipe-separated, * = all -->
<key>allowedResponseHeaders</key><value>*</value>                     <!-- pipe-separated, * = all -->
```

**Dynamic overrides:**
- `CamelHttpUri` → overrides full URI
- `CamelHttpQuery` → overrides query string
- Set `SAP.DisableAttachments.HTTP=true` to disable MPL error attachments

---

### OData V2 Receiver (v1.24.0 — confirmed from live tenant)
```xml
<key>ComponentType</key><value>HCIOData</value>
<key>ComponentNS</key><value>sap</value>
<key>componentVersion</key><value>1.24</value>
<key>Name</key><value>OData</value>
<key>Description</key><value/>
<key>TransportProtocolVersion</key><value>1.24.0</value>
<key>ComponentSWCVName</key><value>external</value>
<key>ComponentSWCVId</key><value>1.24.0</value>
<key>TransportProtocol</key><value>HTTP</value>
<key>MessageProtocol</key><value>OData V2</value>
<key>MessageProtocolVersion</key><value>1.24.0</value>
<key>direction</key><value>Receiver</value>
<key>system</key><value>S4HANA_System</value>
<key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:HCIOData/tp::HTTP/mp::OData V2/direction::Receiver/version::1.24.0</value>
<!-- Connection Tab -->
<key>address</key><value>{{S4_OData_Address}}</value>
<key>proxyType</key><value>Internet</value>                           <!-- Internet | On-Premise -->
<key>scc_location_id</key><value>{{S4_OData_LocId}}</value>          <!-- Cloud Connector Location ID -->
<key>authenticationMethod</key><value>{{S4_OData_Auth}}</value>      <!-- None|Basic|Principal Propagation|Client Certificate|OAuth2 Client Credentials -->
<key>alias</key><value>{{S4_OData_Cred}}</value>                     <!-- credential alias (Basic/OAuth) -->
<key>isCSRFEnabled</key><value>{{S4_OData_CSRF}}</value>             <!-- true|false -->
<key>enableTLSSessionReuse</key><value>{{S4_OData_Reuse}}</value>    <!-- true|false -->
<!-- Processing Tab -->
<key>operation</key><value>Query(GET)</value>                         <!-- Query(GET)|Create(POST)|Update(PUT)|Merge|Read(GET)|Delete|Patch|Function Import|Dynamic -->
<key>resourcePath</key><value>{{S4_OData_ResourcePath}}</value>      <!-- e.g. A_Product, or EntitySet(key=value) -->
<key>queryOptions</key><value>{{S4_OData_Query}}</value>             <!-- $filter=..., $expand=..., $select=... -->
<key>customQueryOptions</key><value>{{S4_OData_CustomQuery}}</value>  <!-- additional query options -->
<key>fields</key><value/>                                             <!-- for POST/PUT/MERGE/PATCH -->
<key>contentType</key><value>application/atom+xml</value>            <!-- application/atom+xml | application/json -->
<key>pagination</key><value>0</value>                                 <!-- 0=disabled -->
<key>enableBatchProcessing</key><value>0</value>                      <!-- 0=disabled -->
<key>enableMPLAttachments</key><value>true</value>
<key>receiveTimeOut</key><value>{{S4_OData_Timeout}}</value>         <!-- minutes -->
<!-- EDMX / Metadata -->
<key>edmxFilePath</key><value>edmx/your_edmx_file.edmx</value>       <!-- relative path to EDMX -->
<key>metadataAllowedURIParams</key><value>{{S4_OData_MetadataCustomQuery}}</value>
<key>metadataAllowedHeaders</key><value/>
<!-- Header Details -->
<key>whitelistRequestHeaders</key><value>{{S4_OData_RequestHeaders}}</value>
<key>whitelistResponseHeaders</key><value/>
<!-- Other -->
<key>odataCertAuthPrivateKeyAlias</key><value/>
<key>apiArtifactType</key><value/>
<key>providerAuth</key><value/>
<key>providerName</key><value/>
<key>providerUrl</key><value/>
<key>providerRelativeUrl</key><value/>
<key>internetProxyType</key><value/>
<key>proxyHost</key><value/>
<key>proxyPort</key><value/>
<key>odatapagesize</key><value/>
<key>characterEncoding</key><value>none</value>
```

**Dynamic overrides:**
- Set `SAP_ODataV2_RefreshCacheOnExpiry=false` to prevent hourly metadata cache reset
- `SAP_connMaxLiveMinutes` — max connection pool lifetime
- `SAP.DisableAttachments.ODataV2=true` — disable MPL error attachments
- Pagination loop property: `${property.<receiver>.<channel>.hasMoreRecords}`

---

### SOAP Receiver (v1.12.3 — ✅ confirmed from live tenant CPI-saved iflw)
**Additional WS-Security fields confirmed from CPI-saved:** `WSSecurity_outbound`, `WSSecurityType_outbound`, `WsdlUserNameTokenCredentialName`, `UserNameTokenOption`, `UserNameTokenCredentialName`, `WSSecurity_SignatureAlgorithm`, `recipientX509TokenAssertion`, `X509TokenAssertion`, `AlgorithmSuiteAssertion`, `InitiatorTokenIncludeStrategy_outbound`, `RecipientTokenIncludeStrategy`, `SetTimeStamp`, `Layout_outbound`, `PrivateKeyAliasSigning`, `PrivateKeyAliasSigning_wsdl`, `PublicKeyAliasEncryption`, `PublicKeyAliasEncryption_wsdl`, `SenderBasicSecurityProfileCompliant`, `SenderBasicSecurityProfileCompliant_wsdl`, `soapWsdlURL`, `soapWsdlPortName`, `soapServiceName`, `operationName`, `sendHttpResponseCode`, `KeepConnectionAlive`
**Note:** `location_id` (underscore) for SOAP — same as SFTP (NOT `locationID` which HTTP uses).
```xml
<key>ComponentType</key><value>SOAP</value>
<key>ComponentNS</key><value>sap</value>
<key>componentVersion</key><value>1.12</value>
<key>Name</key><value>SOAP</value>
<key>Description</key><value/>
<key>TransportProtocolVersion</key><value>1.12.3</value>
<key>ComponentSWCVName</key><value>external</value>
<key>ComponentSWCVId</key><value>1.12.3</value>
<key>TransportProtocol</key><value>HTTP</value>
<key>MessageProtocol</key><value>SOAP 1.x</value>
<key>MessageProtocolVersion</key><value>1.12.3</value>
<key>direction</key><value>Receiver</value>
<key>system</key><value>SOAPSystem</value>
<key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:SOAP/tp::HTTP/mp::SOAP 1.x/direction::Receiver/version::1.12.3</value>
<!-- Connection Tab -->
<key>address</key><value>{{SOAP_Endpoint_URL}}</value>
<key>proxyType</key><value>default</value>                            <!-- default=Internet | On-Premise | Manual -->
<key>locationID</key><value/>                                         <!-- On-Premise only -->
<key>authentication</key><value>Basic</value>                         <!-- None|Basic|Client Certificate|Principal Propagation|OAuth 2.0 SAML Bearer -->
<key>credentialName</key><value>{{SOAP_Credential}}</value>
<key>privateKeyAlias</key><value/>                                    <!-- Client Certificate only -->
<key>requestTimeout</key><value>{{SOAP_Timeout}}</value>             <!-- ms, default 60000 -->
<key>keepAlive</key><value>false</value>                              <!-- keep-alive connection -->
<key>CompressMessage</key><value>0</value>                            <!-- 0=no, 1=yes -->
<key>allowChunking</key><value>true</value>
<key>cleanupHeaders</key><value>true</value>
<key>returnHttpResponseCodeAsHeader</key><value>false</value>         <!-- writes to CamelHttpResponseCode -->
<!-- WS-Security Tab (optional) -->
<key>wsSecurityType</key><value>None</value>                          <!-- None|Sign Message|Sign and Encrypt Message -->
<key>wsSecConfig</key><value>None</value>                             <!-- Via Manual Configuration|Based on Policies in WSDL|None -->
```

---

### SFTP Receiver (v1.13.3 — ✅ CONFIRMED from live tenant CPI-saved iflw, May 2026)
#### ⚠️ ALL property key names below are DIFFERENT from SAP help docs — use these exact keys.
#### `host` is SEPARATE (NOT combined address). `MessageProtocol=File` (NOT None).
#### Boolean values are `0`/`1` (NOT `true`/`false`). Auth value is `public_key`/`user_password`.
#### SFTP uses `activityType=Send` on the ServiceTask (NOT ExternalCall like HTTP/SOAP).
```xml
<!-- Identity -->
<key>ComponentType</key><value>SFTP</value>
<key>ComponentNS</key><value>sap</value>
<key>componentVersion</key><value>1.13</value>
<key>Name</key><value>SFTP</value>
<key>Description</key><value/>
<key>TransportProtocolVersion</key><value>1.20.1</value>
<key>ComponentSWCVName</key><value>external</value>
<key>ComponentSWCVId</key><value>1.20.1</value>
<key>TransportProtocol</key><value>SFTP</value>
<key>MessageProtocol</key><value>File</value>                         <!-- ← NOT None -->
<key>MessageProtocolVersion</key><value>1.20.1</value>
<key>direction</key><value>Receiver</value>
<key>system</key><value>SFTPSystem</value>
<key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:SFTP/tp::SFTP/mp::File/direction::Receiver/version::1.13.3</value>
<key>sftpSecEnabled</key><value>1</value>                             <!-- ← new required field -->
<!-- Connection -->
<key>host</key><value>{{SFTP_Host}}</value>                           <!-- host ONLY — no port here. NOT combined 'address' key -->
<key>username</key><value>{{SFTP_User}}</value>                       <!-- ← 'username' not 'userName' -->
<key>authentication</key><value>public_key</value>                    <!-- public_key | user_password | dual -->
<key>privateKeyAlias</key><value>{{SFTP_PrivateKeyAlias}}</value>    <!-- for public_key auth -->
<key>credential_name</key><value/>                                    <!-- ← 'credential_name' not 'credentialName' — for user_password auth -->
<key>proxyType</key><value>none</value>                               <!-- none | internet | onPremise -->
<key>proxyHost</key><value/>
<key>proxyPort</key><value/>
<key>proxyProtocol</key><value>socks5</value>
<key>proxyAlias</key><value/>
<key>location_id</key><value/>                                        <!-- ← 'location_id' not 'scc_location_id' -->
<key>connectTimeout</key><value>10000</value>                         <!-- ← 'connectTimeout' not 'timeout' -->
<key>maximumReconnectAttempts</key><value>3</value>                   <!-- ← 'maximumReconnectAttempts' not 'maxReconnectAttempts' -->
<key>reconnectDelay</key><value>1000</value>
<key>disconnect</key><value>0</value>                                 <!-- ← 0/1 not true/false -->
<key>allowDeprecatedAlgorithms</key><value>0</value>                  <!-- ← 'allowDeprecatedAlgorithms' not 'enableDeprecatedAlgorithms' -->
<!-- File/Directory -->
<key>path</key><value>{{SFTP_Directory}}</value>                      <!-- ← 'path' not 'directory' -->
<key>fileName</key><value>output_${property.msgId}.xml</value>
<key>fileAppendTimeStamp</key><value>0</value>                        <!-- ← 'fileAppendTimeStamp' not 'appendTimestamp' -->
<!-- Processing -->
<key>fileExist</key><value>Override</value>                           <!-- ← 'fileExist' not 'fileExistHandling'. Values: Override|Append|Fail|Ignore -->
<key>stepwise</key><value>1</value>                                   <!-- ← 1/0 not true/false -->
<key>autoCreate</key><value>1</value>
<key>flatten</key><value/>
<key>fastExistsCheck</key><value>1</value>
<key>useTempFile</key><value>0</value>                                <!-- ← 'useTempFile' not 'useTmpFile' -->
<key>tempFileName</key><value>${file:name}.tmp</value>                <!-- ← 'tempFileName' not 'tmpFileName' -->
```

**⚠️ SFTP ServiceTask uses `activityType=Send` (NOT ExternalCall — confirmed from CPI-saved iflw):**
```xml
<!-- SFTP uses Send, HTTP/SOAP use ExternalCall -->
<bpmn2:serviceTask id="ServiceTask_SFTP" name="Send to SFTP">
    <bpmn2:extensionElements>
        <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
        <ifl:property><key>activityType</key><value>Send</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::Send/version::1.0.4</value></ifl:property>
    </bpmn2:extensionElements>
</bpmn2:serviceTask>
```

**Dynamic runtime overrides (SAP_Ftp* properties):**
```
SAP_FtpProxyType    → proxyType  (internet | onPremise)
SAP_FtpAuthMethod   → authMethod
SAP_FtpTimeout      → timeout
SAP_FtpMaxReconnect → maxReconnectAttempts
SAP_FtpMaxReconDelay→ reconnectDelay
SAP_FtpDisconnect   → disconnect  (true | false)
SAP_FtpStepwise     → stepwise    (true | false)
SAP_FtpCreateDir    → autoCreate  (true | false)
SAP_FtpFlattenFileName → flatten  (true | false)
SAP_FtpFastExistsCheck → fastExistsCheck (true | false)
SAP_FtpAfterProc    → fileExistHandling (Override | Append | Fail | Ignore)
CamelFileName       → dynamic file name
```
**MPL properties set by adapter:**
- `ProducedFile` — actual file path written

---

### ProcessDirect Receiver (v1.1.1)
```xml
<key>ComponentType</key><value>ProcessDirect</value>
<key>ComponentNS</key><value>sap</value>
<key>Vendor</key><value>SAP</value>
<key>componentVersion</key><value>1.1</value>
<key>Name</key><value>ProcessDirect</value>
<key>Description</key><value/>
<key>TransportProtocolVersion</key><value>1.1.2</value>
<key>ComponentSWCVName</key><value>external</value>
<key>ComponentSWCVId</key><value>1.1.2</value>
<key>TransportProtocol</key><value>Not Applicable</value>
<key>MessageProtocol</key><value>Not Applicable</value>
<key>MessageProtocolVersion</key><value>1.1.2</value>
<key>direction</key><value>Receiver</value>
<key>system</key><value>TargetSystem</value>
<key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::ProcessDirect/vendor::SAP/tp::Not Applicable/mp::Not Applicable/direction::Receiver/version::1.1.1</value>
<!-- Connection Tab -->
<key>address</key><value>{{ProcessDirect_Address}}</value>            <!-- address of consumer iFlow's PD sender, e.g. /myConsumerFlow -->
```

**Notes:**
- Alphanumeric + `_` and `-` allowed in address. May or may not start with `/`.
- Supports simple expressions: `${header.address}`.
- Do NOT use `<Send>` component with ProcessDirect adapter.

---

### IDoc Receiver
```xml
<key>ComponentType</key><value>IDoc</value>
<key>ComponentNS</key><value>sap</value>
<key>componentVersion</key><value>1.x</value>                        <!-- verify on tenant -->
<key>Name</key><value>IDoc</value>
<key>Description</key><value/>
<key>TransportProtocol</key><value>HTTP</value>
<key>MessageProtocol</key><value>IDoc</value>
<key>direction</key><value>Receiver</value>
<key>system</key><value>S4HANA</value>
<key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:IDoc/tp::HTTP/mp::IDoc/direction::Receiver/version::1.x.x</value>  <!-- ⚠️ verify version -->
<!-- Connection Tab -->
<key>address</key><value>{{IDoc_Endpoint_URL}}</value>
<key>proxyType</key><value>Internet</value>                           <!-- Internet | On-Premise | Manual -->
<key>locationID</key><value/>
<key>iDocContentType</key><value>Application/x-sap.idoc</value>      <!-- Application/x-sap.idoc | Text/XML -->
<key>authentication</key><value>Basic</value>                         <!-- Basic | Client Certificate | None | Principal Propagation -->
<key>credentialName</key><value>{{IDoc_Credential}}</value>
<key>privateKeyAlias</key><value/>
<key>requestTimeout</key><value>60000</value>
<key>CompressMessage</key><value>0</value>
<key>allowChunking</key><value>true</value>
<key>returnHttpResponseCodeAsHeader</key><value>false</value>
<key>cleanupHeaders</key><value>true</value>
<!-- Processing Tab -->
<key>sapMessageIdDetermination</key><value>Reuse</value>             <!-- Generate | Reuse | Map -->
<key>sourceForSapMessageId</key><value/>                              <!-- only for Map; ${header.x} or ${property.x} -->
```

**Headers set by IDoc Adapter:**
- `SOAPAction`, `SapIDocType`, `SapIDocTransferId`, `SapIDocDbId`, `SapMessageId`, `SapIDocAssignMap`

---

### Mail Receiver
```xml
<key>ComponentType</key><value>Mail</value>
<key>ComponentNS</key><value>sap</value>
<key>componentVersion</key><value>x.x</value>                        <!-- verify on tenant -->
<key>Name</key><value>Mail</value>
<key>Description</key><value/>
<key>TransportProtocol</key><value>SMTP</value>
<key>MessageProtocol</key><value>None</value>
<key>direction</key><value>Receiver</value>
<key>system</key><value>MailServer</value>
<key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:Mail/tp::SMTP/mp::None/direction::Receiver/version::x.x.x</value>  <!-- ⚠️ verify version -->
<!-- Connection Tab -->
<key>address</key><value>smtp.server.com:587</value>                  <!-- host:port, e.g. smtp.mail.yahoo.com:465 -->
<key>proxyType</key><value>Internet</value>                           <!-- Internet | On-Premise -->
<key>locationID</key><value/>
<key>timeout</key><value>30000</value>                                <!-- ms, default 30000, max 300000 -->
<key>protection</key><value>STARTTLS Mandatory</value>                <!-- Off | STARTTLS Mandatory | STARTTLS Optional | SMTPS -->
<key>authentication</key><value>Plain User Name/Password</value>      <!-- None | Plain User Name/Password | Encrypted User/Password | OAuth2 Authorization Code -->
<key>credentialName</key><value>{{Mail_Credential}}</value>
<!-- Processing Tab -->
<key>from</key><value>{{Mail_From}}</value>
<key>to</key><value>{{Mail_To}}</value>                               <!-- comma-separated for multiple -->
<key>cc</key><value/>
<key>bcc</key><value/>
<key>subject</key><value>{{Mail_Subject}}</value>
<key>mailBody</key><value>${in.body}</value>
<key>bodyMimeType</key><value>Text/Plain</value>                      <!-- Text/Plain | Text/HTML | Application/XML | Application/JSON | etc. -->
<key>bodyEncoding</key><value>UTF-8</value>                           <!-- UTF-8 | windows-1252 | ISO-8859-1 -->
<key>contentTransferEncoding</key><value>Automatic</value>            <!-- Automatic | 7Bit | 8Bit | Base64 | Binary | Quoted-Printable -->
```

---

## COMPLETE PALETTE STEP FORMATS
### (Source: SAP official docs + confirmed live tenant patterns)

---

### Message Start Event (HTTPS-triggered)
```xml
<bpmn2:startEvent id="StartEvent_1" name="Receive Message">
    <bpmn2:extensionElements>
        <ifl:property>
            <key>cmdVariantUri</key>
            <value>ctype::FlowstepVariant/cname::MessageStartEvent</value>
        </ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:outgoing>SF_1</bpmn2:outgoing>
    <bpmn2:messageEventDefinition/>
</bpmn2:startEvent>
```

### Timer Start Event
```xml
<bpmn2:startEvent id="StartEvent_1" name="Timer Start">
    <bpmn2:extensionElements>
        <ifl:property><key>activityType</key><value>StartTimerEvent</value></ifl:property>
        <ifl:property><key>scheduleKey</key><value>{{Scheduler}}</value></ifl:property>
        <ifl:property><key>componentVersion</key><value>1.3</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::intermediatetimer/version::1.3.0</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:outgoing>SF_1</bpmn2:outgoing>
    <bpmn2:timerEventDefinition/>
</bpmn2:startEvent>
```
⚠️ MUST include `<bpmn2:timerEventDefinition/>`. MUST NOT include `intervalInMinutes` or `runOnce`.
⚠️ scheduleKey value MUST be `{{Scheduler}}`. Configure interval in CPI UI after import.

### Message End Event
```xml
<bpmn2:endEvent id="EndEvent_1" name="End">
    <bpmn2:extensionElements>
        <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::MessageEndEvent/version::1.1.0</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SF_N</bpmn2:incoming>
    <bpmn2:messageEventDefinition/>
</bpmn2:endEvent>
```

### Content Modifier (Enricher v1.5.3)
**Source Type values:** `constant` | `header` | `property` | `xpath` | `expression` | `external parameter` | `localVariable` | `globalVariable`
```xml
<bpmn2:callActivity id="CallActivity_CM" name="Set Headers and Properties">
    <bpmn2:extensionElements>
        <ifl:property><key>bodyType</key><value>expression</value></ifl:property>
        <ifl:property>
            <key>headerTable</key>
            <value>&lt;row&gt;&lt;cell id='Action'&gt;Create&lt;/cell&gt;&lt;cell id='Type'&gt;constant&lt;/cell&gt;&lt;cell id='Value'&gt;application/xml&lt;/cell&gt;&lt;cell id='Default'&gt;&lt;/cell&gt;&lt;cell id='Name'&gt;Content-Type&lt;/cell&gt;&lt;cell id='Datatype'&gt;&lt;/cell&gt;&lt;/row&gt;</value>
        </ifl:property>
        <ifl:property>
            <key>propertyTable</key>
            <value>&lt;row&gt;&lt;cell id='Action'&gt;Create&lt;/cell&gt;&lt;cell id='Type'&gt;expression&lt;/cell&gt;&lt;cell id='Value'&gt;${date:now:yyyyMMddHHmmssSSS}&lt;/cell&gt;&lt;cell id='Default'&gt;&lt;/cell&gt;&lt;cell id='Name'&gt;processingTimestamp&lt;/cell&gt;&lt;cell id='Datatype'&gt;&lt;/cell&gt;&lt;/row&gt;</value>
        </ifl:property>
        <ifl:property><key>wrapContent</key><value/></ifl:property>
        <ifl:property><key>componentVersion</key><value>1.5</value></ifl:property>
        <ifl:property><key>activityType</key><value>Enricher</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::Enricher/version::1.5.3</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SF_N</bpmn2:incoming>
    <bpmn2:outgoing>SF_N</bpmn2:outgoing>
</bpmn2:callActivity>
```

**Row cell IDs for header/propertyTable:** `Action` (Create|Delete) | `Type` (source type) | `Value` | `Default` | `Name` | `Datatype`
**Body Tab:** `bodyType` = `constant` or `expression` (use `expression` if body has `${...}`)

### Groovy Script (v1.1.2)
```xml
<bpmn2:callActivity id="CallActivity_GS" name="My Script">
    <bpmn2:extensionElements>
        <ifl:property><key>scriptFunction</key><value>processData</value></ifl:property>
        <ifl:property><key>scriptBundleId</key><value/></ifl:property>
        <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
        <ifl:property><key>activityType</key><value>Script</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::GroovyScript/version::1.1.2</value></ifl:property>
        <ifl:property><key>subActivityType</key><value>GroovyScript</value></ifl:property>
        <ifl:property><key>script</key><value>MyScript.groovy</value></ifl:property>   <!-- filename only, no path -->
    </bpmn2:extensionElements>
    <bpmn2:incoming>SF_N</bpmn2:incoming>
    <bpmn2:outgoing>SF_N</bpmn2:outgoing>
</bpmn2:callActivity>
```
**Groovy Runtime:** v2.4.21 (Script v1.1) / v4.0.29 (Script v2.0). Java 8 stdlib available.

### Request Reply (ExternalCall — bpmn2:serviceTask NOT callActivity)
```xml
<bpmn2:serviceTask id="ServiceTask_RR" name="Call External System">
    <bpmn2:extensionElements>
        <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
        <ifl:property><key>activityType</key><value>ExternalCall</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::ExternalCall/version::1.0.4</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SF_N</bpmn2:incoming>
    <bpmn2:outgoing>SF_N</bpmn2:outgoing>
</bpmn2:serviceTask>
```
⚠️ Always `bpmn2:serviceTask`, NEVER `bpmn2:callActivity` for Request Reply.

### Message Mapping (v1.3.1)
```xml
<bpmn2:callActivity id="CallActivity_MM" name="Map to Target">
    <bpmn2:extensionElements>
        <ifl:property><key>mappinguri</key><value>dir://mmap/src/main/resources/mapping/MyMapping.mmap</value></ifl:property>
        <ifl:property><key>mappingname</key><value>MyMapping</value></ifl:property>
        <ifl:property><key>mappingType</key><value>MessageMapping</value></ifl:property>
        <ifl:property><key>mappingReference</key><value>static</value></ifl:property>   <!-- static | dynamic -->
        <ifl:property><key>mappingpath</key><value>src/main/resources/mapping/MyMapping</value></ifl:property>
        <ifl:property><key>componentVersion</key><value>1.3</value></ifl:property>
        <ifl:property><key>activityType</key><value>Mapping</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::MessageMapping/version::1.3.1</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SF_N</bpmn2:incoming>
    <bpmn2:outgoing>SF_N</bpmn2:outgoing>
</bpmn2:callActivity>
```
**Dynamic reference:** set `mappingReference=dynamic`, value = `${header.x}` resolving to `ref:<mapping_ID>`

### Router (CBR) — confirmed from CPI-saved iflw (May 2026)
```xml
<!-- Gateway element — NOT callActivity. Has extensionElements + default attribute. -->
<bpmn2:exclusiveGateway default="SF_DefaultBranch" id="ExclusiveGateway_Router" name="Route by Condition">
    <bpmn2:extensionElements>
        <ifl:property><key>raiseAlert</key><value>false</value></ifl:property>
        <ifl:property><key>activityType</key><value>ExclusiveGateway</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::ExclusiveGateway</value></ifl:property>   <!-- NO version — confirmed from CPI-saved iflw -->
        <ifl:property><key>throwException</key><value>false</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SF_in</bpmn2:incoming>
    <bpmn2:outgoing>SF_Branch1</bpmn2:outgoing>
    <bpmn2:outgoing>SF_Branch2</bpmn2:outgoing>
    <bpmn2:outgoing>SF_Default</bpmn2:outgoing>
</bpmn2:exclusiveGateway>

<!-- Branch with condition -->
<bpmn2:sequenceFlow id="SF_Branch1" name="Branch 1"
    sourceRef="ExclusiveGateway_Router" targetRef="NextStep_1">
    <bpmn2:extensionElements>
        <ifl:property><key>expressionType</key><value>Non-XML</value></ifl:property>
        <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::GatewayRoute/version::1.0.0</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:conditionExpression id="FormalExpression_SF_Branch1"
        xsi:type="bpmn2:tFormalExpression">${property.myProp} = 'value1'</bpmn2:conditionExpression>
</bpmn2:sequenceFlow>

<!-- XPath condition branch -->
<bpmn2:sequenceFlow id="SF_Branch2" name="Branch 2"
    sourceRef="ExclusiveGateway_Router" targetRef="NextStep_2">
    <bpmn2:extensionElements>
        <ifl:property><key>expressionType</key><value>XML</value></ifl:property>
        <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::GatewayRoute/version::1.0.0</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:conditionExpression id="FormalExpression_SF_Branch2"
        xsi:type="bpmn2:tFormalExpression">count(/Root/Items) &gt; 0</bpmn2:conditionExpression>
</bpmn2:sequenceFlow>
```

**Non-XML condition operators:** `=` `!=` `>` `>=` `<` `<=` `and` `or` `contains` `not contains` `in` `not in` `regex` `not regex`
**Variable syntax:** `${header.x}` | `${property.x}` | `${exception.message}`
**BPMNShape:** `height="40.0" width="40.0"` (diamond)

### General Splitter (v1.6.0)
```xml
<bpmn2:callActivity id="CallActivity_Split" name="Split Messages">
    <bpmn2:extensionElements>
        <ifl:property><key>xpathExpression</key><value>/Root/Item</value></ifl:property>
        <ifl:property><key>grouping</key><value>1</value></ifl:property>             <!-- or ${header.x} -->
        <ifl:property><key>streaming</key><value>false</value></ifl:property>
        <ifl:property><key>parallelProcessing</key><value>false</value></ifl:property>
        <ifl:property><key>numberOfConcurrentProcesses</key><value>10</value></ifl:property>  <!-- 1-50 -->
        <ifl:property><key>timeout</key><value>300</value></ifl:property>             <!-- seconds -->
        <ifl:property><key>stopOnException</key><value>false</value></ifl:property>
        <ifl:property><key>componentVersion</key><value>1.6</value></ifl:property>
        <ifl:property><key>activityType</key><value>Splitter</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::GeneralSplitter/version::1.6.0</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SF_N</bpmn2:incoming>
    <bpmn2:outgoing>SF_N</bpmn2:outgoing>
</bpmn2:callActivity>
```
**Camel headers set:** `CamelSplitIndex` (0-based) | `CamelSplitSize` | `CamelSplitComplete` (boolean)

### Gather (v1.2.0)
```xml
<bpmn2:callActivity id="CallActivity_Gather" name="Gather Messages">
    <bpmn2:extensionElements>
        <ifl:property><key>incomingFormat</key><value>XML (Same Format)</value></ifl:property>
        <!-- XML (Same Format) | XML (Different Format) | Plain Text | Any -->
        <ifl:property><key>aggregationAlgorithm</key><value>Combine</value></ifl:property>
        <!-- Combine | Combine at XPath | Concatenate | Zip | Tar -->
        <ifl:property><key>xpathForSrc</key><value>/Root/Items</value></ifl:property>   <!-- Combine at XPath only -->
        <ifl:property><key>xpathForTgt</key><value>/MergedRoot</value></ifl:property>   <!-- Combine at XPath only -->
        <ifl:property><key>fileName</key><value/></ifl:property>                         <!-- Zip/Tar only -->
        <ifl:property><key>componentVersion</key><value>1.2</value></ifl:property>
        <ifl:property><key>activityType</key><value>Gather</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::Gather/version::1.2.0</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SF_N</bpmn2:incoming>
    <bpmn2:outgoing>SF_N</bpmn2:outgoing>
</bpmn2:callActivity>
```

### Filter (v1.1.0)
```xml
<bpmn2:callActivity id="CallActivity_Filter" name="Filter">
    <bpmn2:extensionElements>
        <ifl:property><key>xpathType</key><value>Nodelist</value></ifl:property>
        <ifl:property><key>wrapContent</key><value>/Root/Item[Status='ACTIVE']</value></ifl:property>
        <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
        <ifl:property><key>activityType</key><value>Filter</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::Filter/version::1.1.0</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SF_N</bpmn2:incoming>
    <bpmn2:outgoing>SF_N</bpmn2:outgoing>
</bpmn2:callActivity>
```

### DataStore Write (put v1.7.1)
```xml
<bpmn2:callActivity id="CallActivity_DS" name="Write to DataStore">
    <bpmn2:extensionElements>
        <ifl:property><key>storageName</key><value>MyDataStore</value></ifl:property>    <!-- max 40 chars, no spaces -->
        <ifl:property><key>visibility</key><value>local</value></ifl:property>           <!-- local=Integration Flow | global=Global -->
        <ifl:property><key>messageId</key><value>${property.msgId}</value></ifl:property> <!-- entry ID, max 255 chars -->
        <ifl:property><key>alert</key><value>2</value></ifl:property>                    <!-- alerting threshold days -->
        <ifl:property><key>expire</key><value>30</value></ifl:property>                  <!-- expiration days, 1-180, default 30 -->
        <ifl:property><key>encrypt</key><value>true</value></ifl:property>               <!-- encrypt at rest -->
        <ifl:property><key>override</key><value>true</value></ifl:property>              <!-- overwrite existing; false → DuplicateEntryException -->
        <ifl:property><key>includeMessageHeaders</key><value>false</value></ifl:property><!-- store headers with payload -->
        <ifl:property><key>componentVersion</key><value>1.7</value></ifl:property>
        <ifl:property><key>activityType</key><value>DBstorage</value></ifl:property>
        <ifl:property><key>operation</key><value>put</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::put/version::1.7.1</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SF_N</bpmn2:incoming>
    <bpmn2:outgoing>SF_N</bpmn2:outgoing>
</bpmn2:callActivity>
```
⚠️ `DuplicateEntryException` from duplicate writes CANNOT be caught by Exception Subprocess.

### Exception Subprocess (v1.1.0)
```xml
<bpmn2:subProcess id="SubProcess_Error" name="Exception Subprocess">
    <!-- NO triggeredByEvent="true" attribute -->
    <bpmn2:extensionElements>
        <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
        <ifl:property><key>activityType</key><value>ErrorEventSubProcessTemplate</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::ErrorEventSubProcessTemplate/version::1.1.0</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:startEvent id="ErrorStartEvent_1" name="Error Start">
        <bpmn2:outgoing>ErrorFlow_1</bpmn2:outgoing>
        <bpmn2:errorEventDefinition>
            <bpmn2:extensionElements>
                <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::ErrorStartEvent</value></ifl:property>
                <ifl:property><key>activityType</key><value>StartErrorEvent</value></ifl:property>
            </bpmn2:extensionElements>
        </bpmn2:errorEventDefinition>
    </bpmn2:startEvent>
    <!-- Add your error handling steps here -->
    <bpmn2:endEvent id="ErrorEndEvent_1" name="Error End">
        <bpmn2:incoming>ErrorFlow_N</bpmn2:incoming>
        <bpmn2:errorEventDefinition>
            <bpmn2:extensionElements>
                <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::ErrorEndEvent</value></ifl:property>
                <ifl:property><key>activityType</key><value>EndErrorEvent</value></ifl:property>
            </bpmn2:extensionElements>
        </bpmn2:errorEventDefinition>
    </bpmn2:endEvent>
    <bpmn2:sequenceFlow id="ErrorFlow_1" sourceRef="ErrorStartEvent_1" targetRef="..."/>
</bpmn2:subProcess>
```

### Local Integration Process (subprocess call)
```xml
<!-- Participant definition -->
<bpmn2:participant id="Participant_Process_2" ifl:type="IntegrationProcess"
    name="My Local Process" processRef="Process_2">
    <bpmn2:extensionElements/>
</bpmn2:participant>

<!-- Call step in main process -->
<bpmn2:callActivity id="CallActivity_PC" name="Call Local Process">
    <bpmn2:extensionElements>
        <ifl:property><key>activityType</key><value>ProcessCallElement</value></ifl:property>
        <ifl:property><key>subActivityType</key><value>NonLoopingProcess</value></ifl:property>
        <ifl:property><key>processId</key><value>Process_2</value></ifl:property>
        <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::NonLoopingProcess/version::1.0.3</value></ifl:property>
    </bpmn2:extensionElements>
</bpmn2:callActivity>

<!-- Local process definition -->
<bpmn2:process id="Process_2" name="My Local Process">
    <bpmn2:extensionElements>
        <ifl:property><key>transactionTimeout</key><value>30</value></ifl:property>
        <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowElementVariant/cname::LocalIntegrationProcess/version::1.1.3</value></ifl:property>
        <ifl:property><key>transactionalHandling</key><value>Not Required</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:startEvent id="Start_LP">
        <bpmn2:extensionElements>
            <ifl:property><key>activityType</key><value>StartEvent</value></ifl:property>
            <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::StartEvent</value></ifl:property>
        </bpmn2:extensionElements>
    </bpmn2:startEvent>
    <bpmn2:endEvent id="End_LP">
        <bpmn2:extensionElements>
            <ifl:property><key>activityType</key><value>EndEvent</value></ifl:property>
            <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::EndEvent</value></ifl:property>
        </bpmn2:extensionElements>
    </bpmn2:endEvent>
</bpmn2:process>
```

---

## FILE FORMATS

### .project
```xml
<?xml version="1.0" encoding="UTF-8"?><projectDescription>
   <name>MyIFlow</name>
   <comment/>
   <projects/>
   <buildSpec>
      <buildCommand>
         <name>org.eclipse.jdt.core.javabuilder</name>
         <arguments/>
      </buildCommand>
   </buildSpec>
   <natures>
      <nature>org.eclipse.jdt.core.javanature</nature>
      <nature>com.sap.ide.ifl.project.support.project.nature</nature>
      <nature>com.sap.ide.ifl.bsn</nature>
   </natures>
</projectDescription>
```

### metainfo.prop
```
#Store metainfo properties
description=Your iFlow description here.
```

### parameters.prop
```
#
#Parameters for MyIFlow
MY_PARAM=default_value
```

### parameters.propdef
```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?><parameters><parameter>
    <key/>
    <name>MY_PARAM</name>
    <type>xsd:string</type>
    <isRequired>true</isRequired>
    <constraint/>
    <description>Description of this parameter</description>
    <additionalMetadata/>
  </parameter><param_references/></parameters>
```

---

## ZIP FILE STRUCTURE (files at root — NO wrapper folder)
```
.project
metainfo.prop
META-INF/MANIFEST.MF                                             ← UTF-8 no-BOM, LF endings, Import-Package REQUIRED
src/main/resources/parameters.prop
src/main/resources/parameters.propdef
src/main/resources/scenarioflows/integrationflow/MyFlow.iflw
src/main/resources/script/MyScript.groovy
src/main/resources/mapping/MyMapping.mmap
src/main/resources/mapping/MyMapping.xsl
src/main/resources/wsdl/SourceSchema.xsd
src/main/resources/xsd/TargetSchema.xsd
src/main/resources/edmx/sap_host_port_path.edmx
```

---

## IFLW BPMN RULES (complete)

1. All steps = `bpmn2:callActivity` EXCEPT: Request Reply = `bpmn2:serviceTask`; Router = `bpmn2:exclusiveGateway`
2. Sender adapter config on `bpmn2:messageFlow` from Participant → StartEvent
3. Receiver adapter config on `bpmn2:messageFlow` from **ServiceTask** → Participant (NEVER from EndEvent)
4. sourceRef in collaboration AND sourceElement in BPMNEdge MUST point to the same element
5. Message-triggered `bpmn2:startEvent` needs `<bpmn2:messageEventDefinition/>`
6. Timer-triggered `bpmn2:startEvent` needs `<bpmn2:timerEventDefinition/>` — NOT messageEventDefinition
7. `bpmn2:endEvent` for message output needs `<bpmn2:messageEventDefinition/>`
8. Script files referenced by filename only (no path) in `<key>script</key>`
9. `bpmndi:BPMNDiagram` section is REQUIRED with `name="Default Collaboration Diagram"`
10. All `<di:waypoint>` must have `xsi:type="dc:Point"` attribute
11. All `<bpmndi:BPMNEdge>` must have `sourceElement` and `targetElement` Shape ID references
12. Main process `cmdVariantUri` = `IntegrationProcess/version::1.2.1`; process `name` = `"Integration Process"`
13. `IFlowConfiguration/version::1.2.4` goes in collaboration extensionElements
14. `<bpmn2:subProcess>` for error handling: NO `triggeredByEvent` attribute
15. Collaboration name = `"Default Collaboration"` always
16. `bpmn2:definitions` has NO `targetNamespace` attribute
17. `Participant_Process_1` has EMPTY `<bpmn2:extensionElements/>`
18. Router = real `bpmn2:exclusiveGateway` + conditions on `bpmn2:sequenceFlow` via `bpmn2:conditionExpression`

---

## GROOVY SCRIPT TEMPLATE

```groovy
import com.sap.gateway.ip.core.customdev.util.Message
import java.text.SimpleDateFormat

def Message processData(Message msg) {
    def props   = msg.getProperties()
    def headers = msg.getHeaders()

    // Unique message ID
    def msgId = "FLOW-" + UUID.randomUUID().toString().replace("-","").substring(0,12).toUpperCase()
    msg.setProperty("msgId", msgId)

    // Timestamp
    def sdf = new SimpleDateFormat("yyyyMMddHHmmssSSS")
    sdf.setTimeZone(TimeZone.getTimeZone("UTC"))
    msg.setProperty("processingTimestamp", sdf.format(new Date()))

    // MPL payload logging (only when enabled)
    def enableLog = props.get("ENABLE_PAYLOAD_LOGGING") ?: "FALSE"
    if ("TRUE".equalsIgnoreCase(enableLog)) {
        def body   = msg.getBody(String)
        def msgLog = messageLogFactory.getMessageLog(msg)
        if (msgLog != null) {
            msgLog.addAttachmentAsString("Payload", body, "application/xml")
            msgLog.setStringAttribute("MessageId", msgId)
        }
    }
    return msg
}
```

---

## TENANT INFO
- Platform: SAP Integration Suite (Cloud Integration / CPI)
- All confirmed versions from 4 live tenant iFlows: Credit_Management_SFA, SalesOrder_ReturnOrder, Customer_Order_xDeltaDoc, Material_Master_RETMES (May 2026)
- Adapter property sets sourced from: SAP-docs/btp-integration-suite GitHub (official, May 2026)
- v4 changes: Full Import-Package in MANIFEST, correct BPMN definitions (no targetNamespace, Default Collaboration name, Participant_Process_1 with empty extensionElements), correct Router pattern (bpmn2:exclusiveGateway + sequenceFlow conditions), correct receiver MessageFlow pattern (ServiceTask→Participant), updated versions (IFlowConfig 1.2.4, IntegrationProcess 1.2.1, HTTP 1.15.0, HTTPS 1.5.0, OData 1.24.0), complete SFTP property set (address=host:port combined, all processing fields), complete HTTP/HTTPS/SOAP/OData/SFTP/ProcessDirect/IDoc/Mail property sets from official SAP docs.
