# CPI IFLOW GENERATOR — TENANT CHEAT SHEET (v3)
# Paste this at the start of any new chat with Claude to get correct iFlows immediately.
# All versions confirmed from live tenant iFlows (May 2026).
# Sources: S4_to_Shroom_SalesOrder, Claim_Invoices, SalesOrder_ReturnOrder,
#          Customer_Order_xDeltaDoc, Material_Master_RETMES, Credit_Management_SFA
#          + S4_Material_Delta_To_ThirdParty (Timer iFlow, confirmed working May 2026)

---

## CONTEXT

I am an SAP Integration Suite (CPI) developer. I need you to generate importable iFlow ZIPs.
Use EXACTLY the versions, formats, and structures below — these are confirmed working on my tenant.
Do NOT guess or use different versions. Do NOT ask for clarification on versions — use these.

---

## ⚠️ CRITICAL RULES — READ FIRST (learned from failed imports)

These rules are NON-NEGOTIABLE. Violating any one of them causes import failure or "unable to load":

### ZIP PACKAGING
1. **Files must be at ZIP root — NO parent folder wrapper.**
   CORRECT: `.project`, `metainfo.prop`, `META-INF/MANIFEST.MF`, `src/...`
   WRONG:   `MyIFlow/.project`, `MyIFlow/metainfo.prop`, `MyIFlow/src/...`
   When zipping, always `cd` into the iFlow folder and zip from there.

### metainfo.prop
2. **`metainfo.prop` contains ONLY a comment line and a description. No bundle keys.**
   ```
   #Store metainfo properties
   description=Your iFlow description here.
   ```
   NEVER use `bundle.symbolicName=`, `Bundle-SymbolicName=`, or `?metainfo=properties` — these all cause upload rejection.

### parameters.propdef
3. **`parameters.propdef` root element is `<parameters>` with `standalone="no"`, NOT `<parameterDefinitions>`.**
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

### MANIFEST.MF
4. **MANIFEST.MF uses LF line endings (not CRLF).** Confirmed from working sample — `$` at end of each line, no `^M`.

### Participants
5. **Receiver/Sender system participants use `ifl:type="EndpointRecevier"` (note: SAP typo — single 'i' in Recevier).**
   Sender uses `ifl:type="EndpointSender"`. IntegrationProcess participant stays as `ifl:type="IntegrationProcess"`.
   Each participant MUST have an inner `<ifl:property><key>ifl:type</key><value>...</value></ifl:property>`.
   ```xml
   <bpmn2:participant id="Participant_ThirdParty" ifl:type="EndpointRecevier" name="ThirdParty">
       <bpmn2:extensionElements>
           <ifl:property><key>ifl:type</key><value>EndpointRecevier</value></ifl:property>
       </bpmn2:extensionElements>
   </bpmn2:participant>
   ```
   NEVER use `ifl:type="System"` — causes silent load failure.

### Collaboration extensionElements
6. **Collaboration MUST include the full property set** — not just `cmdVariantUri`. Missing properties cause "unable to load":
   ```xml
   <ifl:property><key>namespaceMapping</key><value/></ifl:property>
   <ifl:property><key>httpSessionHandling</key><value>None</value></ifl:property>
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
   <ifl:property><key>cmdVariantUri</key><value>ctype::IFlowVariant/cname::IFlowConfiguration/version::1.2.3</value></ifl:property>
   ```

### Timer Start Event
7. **Timer startEvent MUST include `<bpmn2:timerEventDefinition/>` and MUST NOT include `intervalInMinutes`, `runOnce`, or any extra properties.**
   Only these 4 properties: `activityType`, `scheduleKey` (value = `{{Scheduler}}`), `componentVersion`, `cmdVariantUri`.
   The 30-min interval is configured manually in CPI UI after import via the Scheduler parameter — it is NOT set in the XML.
   ```xml
   <bpmn2:startEvent id="StartEvent_1" name="Timer Start">
       <bpmn2:extensionElements>
           <ifl:property><key>activityType</key><value>StartTimerEvent</value></ifl:property>
           <ifl:property><key>scheduleKey</key><value>{{Scheduler}}</value></ifl:property>
           <ifl:property><key>componentVersion</key><value>1.3</value></ifl:property>
           <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::intermediatetimer/version::1.3.0</value></ifl:property>
       </bpmn2:extensionElements>
       <bpmn2:outgoing>SequenceFlow_1</bpmn2:outgoing>
       <bpmn2:timerEventDefinition/>
   </bpmn2:startEvent>
   ```

### Exception Subprocess
8. **`<bpmn2:subProcess>` MUST NOT have `triggeredByEvent="true"` attribute.** Use plain `<bpmn2:subProcess id="SubProcess_Error" name="Exception Subprocess">`.

### BPMN Diagram
9. **Every `<di:waypoint>` MUST have `xsi:type="dc:Point"` attribute.**
   CORRECT: `<di:waypoint x="192.0" xsi:type="dc:Point" y="160.0"/>`
   WRONG:   `<di:waypoint x="192.0" y="160.0"/>`

10. **Every `<bpmndi:BPMNEdge>` MUST have `sourceElement` and `targetElement` attributes** referencing the Shape IDs.
    ```xml
    <bpmndi:BPMNEdge bpmnElement="SequenceFlow_1" id="BPMNEdge_SequenceFlow_1"
        sourceElement="BPMNShape_StartEvent_1" targetElement="BPMNShape_CallActivity_1">
    ```

11. **Shape IDs follow the pattern `BPMNShape_<bpmnElement>` and Edge IDs follow `BPMNEdge_<bpmnElement>`.**

12. **`<bpmndi:BPMNDiagram>` must have `name="Default Collaboration Diagram"` attribute.**

### iflw XML style
13. **The `.iflw` file uses indented multi-line XML (4-space indent), NOT single-line/minified XML.**
    Each `<ifl:property>` block uses separate lines for `<key>` and `<value>`.

---

## CONFIRMED STEP VERSIONS — COMPLETE TABLE

### Flow Steps (all use bpmn2:callActivity unless noted)

```
Step Type              activityType              cmdVariantUri
─────────────────────────────────────────────────────────────────────────────────────
Groovy Script          Script                    ctype::FlowstepVariant/cname::GroovyScript/version::1.1.2
Content Modifier       Enricher                  ctype::FlowstepVariant/cname::Enricher/version::1.5.1   ← basic
Content Modifier       Enricher                  ctype::FlowstepVariant/cname::Enricher/version::1.5.3   ← also valid
Content Modifier       Enricher                  ctype::FlowstepVariant/cname::Enricher/version::1.6.0   ← latest
Content Modifier       Enricher                  ctype::FlowstepVariant/cname::Enricher/version::1.6.1   ← also valid
Request Reply          ExternalCall              ctype::FlowstepVariant/cname::ExternalCall/version::1.0.4
JSON to XML            JsonToXmlConverter        ctype::FlowstepVariant/cname::JsonToXmlConverter/version::1.0
JSON to XML (newer)    JsonToXmlConverter        ctype::FlowstepVariant/cname::JsonToXmlConverter/version::1.1.2
XML to JSON            XmlToJsonConverter        ctype::FlowstepVariant/cname::XmlToJsonConverter/version::1.0.8
Message Mapping        Mapping                   ctype::FlowstepVariant/cname::MessageMapping/version::1.3.1
DataStore Write        DBstorage                 ctype::FlowstepVariant/cname::put/version::1.7.1
Router (CBR)           ExclusiveGateway          ctype::FlowstepVariant/cname::ExclusiveGateway/version::1.1.2
Router Branch          GatewayRoute              ctype::FlowstepVariant/cname::GatewayRoute/version::1.0.0
General Splitter       Splitter                  ctype::FlowstepVariant/cname::GeneralSplitter/version::1.6.0
Iterating Splitter     Splitter                  ctype::FlowstepVariant/cname::Camel/version::1.5.1
Gather                 Gather                    ctype::FlowstepVariant/cname::Gather/version::1.2.0
Join                   Join                      ctype::FlowstepVariant/cname::Join/version::1.0.0
Sequential Multicast   SequentialMulticast       ctype::FlowstepVariant/cname::SequentialMulticast/version::1.1.0
Content Enricher       contentEnricherWithLookup ctype::FlowstepVariant/cname::contentEnricherWithLookup/version::1.2.0
Filter                 Filter                    ctype::FlowstepVariant/cname::Filter/version::1.1.0
ZIP Compress           Encoder                   ctype::FlowstepVariant/cname::ZIP Compress/version::1.0.1
Base64 Encode          Encoder                   ctype::FlowstepVariant/cname::Base64 Encode/version::1.0.1
Timer (start)          StartTimerEvent           ctype::FlowstepVariant/cname::intermediatetimer/version::1.3.0
Timer (start newer)    StartTimerEvent           ctype::FlowstepVariant/cname::intermediatetimer/version::1.4.0
Error Subprocess       ErrorEventSubProcessTemplate  ctype::FlowstepVariant/cname::ErrorEventSubProcessTemplate/version::1.0.2
Error Subprocess (new) ErrorEventSubProcessTemplate  ctype::FlowstepVariant/cname::ErrorEventSubProcessTemplate/version::1.1.0
Message End Event      (none)                    ctype::FlowstepVariant/cname::MessageEndEvent/version::1.1.0
Message Start Event    (none)                    ctype::FlowstepVariant/cname::MessageStartEvent   (no version)
Error End Event        EndErrorEvent             ctype::FlowstepVariant/cname::ErrorEndEvent  (no version)
Error Start Event      StartErrorEvent           ctype::FlowstepVariant/cname::ErrorStartEvent  (no version)
Local Process End      EndEvent                  ctype::FlowstepVariant/cname::EndEvent  (no version)
Local Process Start    StartEvent                ctype::FlowstepVariant/cname::StartEvent  (no version)
Process Call           ProcessCallElement        ctype::FlowstepVariant/cname::NonLoopingProcess/version::1.0.3
Loop Process           ProcessCallElement        ctype::FlowstepVariant/cname::LoopingProcess/version::1.3.0
```

### Flow Elements

```
IntegrationProcess      ctype::FlowElementVariant/cname::IntegrationProcess/version::1.2.0   ← use this
IntegrationProcess      ctype::FlowElementVariant/cname::IntegrationProcess/version::1.2.1   ← also valid
LocalIntegrationProcess ctype::FlowElementVariant/cname::LocalIntegrationProcess/version::1.1.3
IFlowConfiguration      ctype::IFlowVariant/cname::IFlowConfiguration/version::1.2.3         ← use this
IFlowConfiguration      ctype::IFlowVariant/cname::IFlowConfiguration/version::1.2.4         ← also valid
```

### Adapters

```
HTTPS Sender      ctype::AdapterVariant/cname::sap:HTTPS/tp::HTTPS/mp::None/direction::Sender/version::1.5.2
HTTPS Sender      ctype::AdapterVariant/cname::sap:HTTPS/tp::HTTPS/mp::None/direction::Sender/version::1.5.0   ← also valid
HTTP Receiver     ctype::AdapterVariant/cname::sap:HTTP/tp::HTTP/mp::None/direction::Receiver/version::1.17.1
HTTP Receiver     ctype::AdapterVariant/cname::sap:HTTP/tp::HTTP/mp::None/direction::Receiver/version::1.15.0  ← also valid
OData Receiver    ctype::AdapterVariant/cname::sap:HCIOData/tp::HTTP/mp::OData V2/direction::Receiver/version::1.27.0  ← newest confirmed
OData Receiver    ctype::AdapterVariant/cname::sap:HCIOData/tp::HTTP/mp::OData V2/direction::Receiver/version::1.25.1  ← also valid
OData Receiver    ctype::AdapterVariant/cname::sap:HCIOData/tp::HTTP/mp::OData V2/direction::Receiver/version::1.25.0  ← also valid
OData Receiver    ctype::AdapterVariant/cname::sap:HCIOData/tp::HTTP/mp::OData V2/direction::Receiver/version::1.24.0  ← also valid
ProcessDirect     ctype::AdapterVariant/cname::ProcessDirect/vendor::SAP/tp::Not Applicable/mp::Not Applicable/direction::Receiver/version::1.1.1
SOAP Receiver     ctype::AdapterVariant/cname::sap:SOAP/tp::HTTP/mp::SOAP 1.x/direction::Receiver/version::1.12.3
```

---

## ADAPTER PROPERTY SETS (exact — copy as-is)

### HTTPS Sender (v1.5.2)
```xml
<key>ComponentType</key><value>HTTPS</value>
<key>ComponentNS</key><value>sap</value>
<key>componentVersion</key><value>1.5</value>
<key>urlPath</key><value>{{Sender_Endpoint_Path}}</value>
<key>Name</key><value>HTTPS</value>
<key>TransportProtocolVersion</key><value>1.5.2</value>
<key>ComponentSWCVName</key><value>external</value>
<key>ComponentSWCVId</key><value>1.5.2</value>
<key>system</key><value>SenderSystem</value>
<key>xsrfProtection</key><value>1</value>
<key>TransportProtocol</key><value>HTTPS</value>
<key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:HTTPS/tp::HTTPS/mp::None/direction::Sender/version::1.5.2</value>
<key>userRole</key><value>ESBMessaging.send</value>
<key>senderAuthType</key><value>RoleBased</value>
<key>MessageProtocol</key><value>None</value>
<key>MessageProtocolVersion</key><value>1.5.2</value>
<key>direction</key><value>Sender</value>
<key>maximumBodySize</key><value>40</value>
```

### HTTP Receiver (v1.17.1)
```xml
<key>ComponentNS</key><value>sap</value>
<key>httpMethod</key><value>POST</value>
<key>allowedResponseHeaders</key><value>*</value>
<key>Name</key><value>HTTP</value>
<key>TransportProtocolVersion</key><value>1.17.1</value>
<key>ComponentSWCVName</key><value>external</value>
<key>streaming</key><value>false</value>
<key>enableMPLAttachments</key><value>true</value>
<key>httpRequestTimeout</key><value>60000</value>
<key>MessageProtocol</key><value>None</value>
<key>ComponentSWCVId</key><value>1.17.1</value>
<key>direction</key><value>Receiver</value>
<key>ComponentType</key><value>HTTP</value>
<key>throwExceptionOnFailure</key><value>true</value>
<key>proxyType</key><value>default</value>
<key>componentVersion</key><value>1.17</value>
<key>retryIteration</key><value>1</value>
<key>retryOnConnectionFailure</key><value>false</value>
<key>system</key><value>ReceiverSystem</value>
<key>authenticationMethod</key><value>Basic</value>
<key>credentialName</key><value>{{Receiver_Credential}}</value>
<key>retryInterval</key><value>5</value>
<key>TransportProtocol</key><value>HTTP</value>
<key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:HTTP/tp::HTTP/mp::None/direction::Receiver/version::1.17.1</value>
<key>MessageProtocolVersion</key><value>1.17.1</value>
<key>httpAddressWithoutQuery</key><value>{{Receiver_Endpoint_URL}}</value>
```

### OData Receiver — HCIOData (use v1.27.0 by default)
```xml
<key>pagination</key><value>0</value>
<key>ComponentNS</key><value>sap</value>
<key>resourcePath</key><value>A_Product</value>
<key>Name</key><value>OData</value>
<key>TransportProtocolVersion</key><value>1.27.0</value>
<key>ComponentSWCVName</key><value>external</value>
<key>enableMPLAttachments</key><value>true</value>
<key>receiveTimeOut</key><value>1</value>
<key>alias</key><value>{{S4_OData_Credential}}</value>
<key>contentType</key><value>application/atom+xml</value>
<key>MessageProtocol</key><value>OData V2</value>
<key>ComponentSWCVId</key><value>1.27.0</value>
<key>direction</key><value>Receiver</value>
<key>ComponentType</key><value>HCIOData</value>
<key>address</key><value>{{S4_OData_BaseURL}}</value>
<key>queryOptions</key><value>$filter=SalesOrder eq '${property.salesOrderId}'&amp;$expand=to_Item</value>
<key>proxyType</key><value>default</value>
<key>isCSRFEnabled</key><value>true</value>
<key>componentVersion</key><value>1.27</value>
<key>enableTLSSessionReuse</key><value>true</value>
<key>system</key><value>S4HANA_OData</value>
<key>authenticationMethod</key><value>Basic</value>
<key>enableBatchProcessing</key><value>0</value>
<key>TransportProtocol</key><value>HTTP</value>
<key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:HCIOData/tp::HTTP/mp::OData V2/direction::Receiver/version::1.27.0</value>
<key>characterEncoding</key><value>none</value>
<key>operation</key><value>Query(GET)</value>
<key>MessageProtocolVersion</key><value>1.27.0</value>
```

### ProcessDirect Receiver (v1.1.1)
```xml
<key>ComponentType</key><value>ProcessDirect</value>
<key>ComponentNS</key><value>sap</value>
<key>Vendor</key><value>SAP</value>
<key>componentVersion</key><value>1.1</value>
<key>address</key><value>{{ProcessDirect_Address}}</value>
<key>Name</key><value>ProcessDirect</value>
<key>TransportProtocolVersion</key><value>1.1.2</value>
<key>ComponentSWCVName</key><value>external</value>
<key>ComponentSWCVId</key><value>1.1.2</value>
<key>system</key><value>TargetSystem</value>
<key>TransportProtocol</key><value>Not Applicable</value>
<key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::ProcessDirect/vendor::SAP/tp::Not Applicable/mp::Not Applicable/direction::Receiver/version::1.1.1</value>
<key>MessageProtocol</key><value>Not Applicable</value>
<key>MessageProtocolVersion</key><value>1.1.2</value>
<key>direction</key><value>Receiver</value>
```

### SOAP Receiver (v1.12.3)
```xml
<key>ComponentType</key><value>SOAP</value>
<key>ComponentNS</key><value>sap</value>
<key>componentVersion</key><value>1.12</value>
<key>address</key><value>{{SOAP_Endpoint_URL}}</value>
<key>Name</key><value>SOAP</value>
<key>TransportProtocolVersion</key><value>1.12.3</value>
<key>ComponentSWCVName</key><value>external</value>
<key>ComponentSWCVId</key><value>1.12.3</value>
<key>MessageProtocol</key><value>SOAP 1.x</value>
<key>MessageProtocolVersion</key><value>1.12.3</value>
<key>TransportProtocol</key><value>HTTP</value>
<key>direction</key><value>Receiver</value>
<key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:SOAP/tp::HTTP/mp::SOAP 1.x/direction::Receiver/version::1.12.3</value>
<key>authentication</key><value>{{SOAP_Auth}}</value>
<key>credentialName</key><value>{{SOAP_Credential}}</value>
<key>requestTimeout</key><value>{{SOAP_Timeout}}</value>
<key>proxyType</key><value>default</value>
<key>CompressMessage</key><value>0</value>
<key>allowChunking</key><value>true</value>
<key>cleanupHeaders</key><value>true</value>
<key>system</key><value>SOAPSystem</value>
```

---

## STEP FORMATS (XML snippets)

### Groovy Script
```xml
<bpmn2:callActivity id="CallActivity_1" name="My Script">
    <bpmn2:extensionElements>
        <ifl:property>
            <key>scriptFunction</key>
            <value>processData</value>
        </ifl:property>
        <ifl:property>
            <key>scriptBundleId</key>
            <value/>
        </ifl:property>
        <ifl:property>
            <key>componentVersion</key>
            <value>1.1</value>
        </ifl:property>
        <ifl:property>
            <key>activityType</key>
            <value>Script</value>
        </ifl:property>
        <ifl:property>
            <key>cmdVariantUri</key>
            <value>ctype::FlowstepVariant/cname::GroovyScript/version::1.1.2</value>
        </ifl:property>
        <ifl:property>
            <key>subActivityType</key>
            <value>GroovyScript</value>
        </ifl:property>
        <ifl:property>
            <key>script</key>
            <value>MyScript.groovy</value>
        </ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SequenceFlow_N</bpmn2:incoming>
    <bpmn2:outgoing>SequenceFlow_N</bpmn2:outgoing>
</bpmn2:callActivity>
```

### Content Modifier (Enricher) — set header + property
```xml
<bpmn2:callActivity id="CallActivity_2" name="Set Headers and Properties">
    <bpmn2:extensionElements>
        <ifl:property>
            <key>componentVersion</key>
            <value>1.5</value>
        </ifl:property>
        <ifl:property>
            <key>activityType</key>
            <value>Enricher</value>
        </ifl:property>
        <ifl:property>
            <key>cmdVariantUri</key>
            <value>ctype::FlowstepVariant/cname::Enricher/version::1.5.1</value>
        </ifl:property>
        <ifl:property>
            <key>bodyType</key>
            <value>expression</value>
        </ifl:property>
        <ifl:property>
            <key>headerTable</key>
            <value>&lt;row&gt;&lt;cell id='Action'&gt;Create&lt;/cell&gt;&lt;cell id='Type'&gt;constant&lt;/cell&gt;&lt;cell id='Value'&gt;application/xml&lt;/cell&gt;&lt;cell id='Default'&gt;&lt;/cell&gt;&lt;cell id='Name'&gt;Content-Type&lt;/cell&gt;&lt;cell id='Datatype'&gt;java.lang.String&lt;/cell&gt;&lt;/row&gt;</value>
        </ifl:property>
        <ifl:property>
            <key>propertyTable</key>
            <value>&lt;row&gt;&lt;cell id='Action'&gt;Create&lt;/cell&gt;&lt;cell id='Type'&gt;constant&lt;/cell&gt;&lt;cell id='Value'&gt;MY_VALUE&lt;/cell&gt;&lt;cell id='Default'&gt;&lt;/cell&gt;&lt;cell id='Name'&gt;MY_PROPERTY&lt;/cell&gt;&lt;cell id='Datatype'&gt;java.lang.String&lt;/cell&gt;&lt;/row&gt;</value>
        </ifl:property>
        <ifl:property>
            <key>wrapContent</key>
            <value/>
        </ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SequenceFlow_N</bpmn2:incoming>
    <bpmn2:outgoing>SequenceFlow_N</bpmn2:outgoing>
</bpmn2:callActivity>
```

### Request Reply (ExternalCall — serviceTask, not callActivity)
```xml
<bpmn2:serviceTask id="ServiceTask_OData" name="Query S4 OData">
    <bpmn2:extensionElements>
        <ifl:property>
            <key>componentVersion</key>
            <value>1.0</value>
        </ifl:property>
        <ifl:property>
            <key>activityType</key>
            <value>ExternalCall</value>
        </ifl:property>
        <ifl:property>
            <key>cmdVariantUri</key>
            <value>ctype::FlowstepVariant/cname::ExternalCall/version::1.0.4</value>
        </ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SequenceFlow_N</bpmn2:incoming>
    <bpmn2:outgoing>SequenceFlow_N</bpmn2:outgoing>
</bpmn2:serviceTask>
```

### Timer Start Event (confirmed working — Timer iFlow)
```xml
<bpmn2:startEvent id="StartEvent_1" name="Timer Start">
    <bpmn2:extensionElements>
        <ifl:property>
            <key>activityType</key>
            <value>StartTimerEvent</value>
        </ifl:property>
        <ifl:property>
            <key>scheduleKey</key>
            <value>{{Scheduler}}</value>
        </ifl:property>
        <ifl:property>
            <key>componentVersion</key>
            <value>1.3</value>
        </ifl:property>
        <ifl:property>
            <key>cmdVariantUri</key>
            <value>ctype::FlowstepVariant/cname::intermediatetimer/version::1.3.0</value>
        </ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:outgoing>SequenceFlow_1</bpmn2:outgoing>
    <bpmn2:timerEventDefinition/>
</bpmn2:startEvent>
```
⚠️ MUST include `<bpmn2:timerEventDefinition/>`. MUST NOT include `intervalInMinutes` or `runOnce`.
⚠️ scheduleKey value MUST be `{{Scheduler}}` — the curly-brace placeholder, not the literal word "Scheduler".
⚠️ Configure the actual interval (e.g. every 30 min) in CPI UI after import via the Scheduler parameter.

### Message Start Event (HTTPS-triggered iFlow)
```xml
<bpmn2:startEvent id="StartEvent_1" name="Start">
    <bpmn2:extensionElements>
        <ifl:property>
            <key>cmdVariantUri</key>
            <value>ctype::FlowstepVariant/cname::MessageStartEvent</value>
        </ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:outgoing>SequenceFlow_1</bpmn2:outgoing>
    <bpmn2:messageEventDefinition/>
</bpmn2:startEvent>
```

### Message End Event
```xml
<bpmn2:endEvent id="EndEvent_1" name="End">
    <bpmn2:extensionElements>
        <ifl:property>
            <key>componentVersion</key>
            <value>1.1</value>
        </ifl:property>
        <ifl:property>
            <key>cmdVariantUri</key>
            <value>ctype::FlowstepVariant/cname::MessageEndEvent/version::1.1.0</value>
        </ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SequenceFlow_N</bpmn2:incoming>
    <bpmn2:messageEventDefinition/>
</bpmn2:endEvent>
```

### Exception Subprocess (confirmed working structure)
```xml
<bpmn2:subProcess id="SubProcess_Error" name="Exception Subprocess">
    <bpmn2:extensionElements>
        <ifl:property>
            <key>componentVersion</key>
            <value>1.1</value>
        </ifl:property>
        <ifl:property>
            <key>activityType</key>
            <value>ErrorEventSubProcessTemplate</value>
        </ifl:property>
        <ifl:property>
            <key>cmdVariantUri</key>
            <value>ctype::FlowstepVariant/cname::ErrorEventSubProcessTemplate/version::1.0.2</value>
        </ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:startEvent id="ErrorStartEvent_1" name="Error Start">
        <bpmn2:outgoing>ErrorFlow_1</bpmn2:outgoing>
        <bpmn2:errorEventDefinition>
            <bpmn2:extensionElements>
                <ifl:property>
                    <key>cmdVariantUri</key>
                    <value>ctype::FlowstepVariant/cname::ErrorStartEvent</value>
                </ifl:property>
                <ifl:property>
                    <key>activityType</key>
                    <value>StartErrorEvent</value>
                </ifl:property>
            </bpmn2:extensionElements>
        </bpmn2:errorEventDefinition>
    </bpmn2:startEvent>
    <bpmn2:endEvent id="ErrorEndEvent_1" name="Error End">
        <bpmn2:incoming>ErrorFlow_1</bpmn2:incoming>
        <bpmn2:errorEventDefinition>
            <bpmn2:extensionElements>
                <ifl:property>
                    <key>cmdVariantUri</key>
                    <value>ctype::FlowstepVariant/cname::ErrorEndEvent</value>
                </ifl:property>
                <ifl:property>
                    <key>activityType</key>
                    <value>EndErrorEvent</value>
                </ifl:property>
            </bpmn2:extensionElements>
        </bpmn2:errorEventDefinition>
    </bpmn2:endEvent>
    <bpmn2:sequenceFlow id="ErrorFlow_1" sourceRef="ErrorStartEvent_1" targetRef="ErrorEndEvent_1"/>
</bpmn2:subProcess>
```
⚠️ NO `triggeredByEvent="true"` attribute on `<bpmn2:subProcess>`.

### DataStore Write (put)
```xml
<bpmn2:callActivity id="CallActivity_DS" name="Write to DataStore">
    <bpmn2:extensionElements>
        <ifl:property><key>visibility</key><value>local</value></ifl:property>
        <ifl:property><key>alert</key><value>2</value></ifl:property>
        <ifl:property><key>encrypt</key><value>true</value></ifl:property>
        <ifl:property><key>expire</key><value>30</value></ifl:property>
        <ifl:property><key>messageId</key><value>${property.msgId}</value></ifl:property>
        <ifl:property><key>componentVersion</key><value>1.7</value></ifl:property>
        <ifl:property><key>override</key><value>true</value></ifl:property>
        <ifl:property><key>activityType</key><value>DBstorage</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::put/version::1.7.1</value></ifl:property>
        <ifl:property><key>operation</key><value>put</value></ifl:property>
        <ifl:property><key>storageName</key><value>MyDataStore</value></ifl:property>
        <ifl:property><key>includeMessageHeaders</key><value>false</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SequenceFlow_N</bpmn2:incoming>
    <bpmn2:outgoing>SequenceFlow_N</bpmn2:outgoing>
</bpmn2:callActivity>
```

### JSON to XML Converter
```xml
<bpmn2:callActivity id="CallActivity_J2X" name="JSON to XML">
    <bpmn2:extensionElements>
        <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
        <ifl:property><key>activityType</key><value>JsonToXmlConverter</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::JsonToXmlConverter/version::1.0</value></ifl:property>
        <ifl:property><key>useNamespaces</key><value>false</value></ifl:property>
        <ifl:property><key>addXMLRootElement</key><value>true</value></ifl:property>
        <ifl:property><key>XMLRootElementName</key><value>Root</value></ifl:property>
        <ifl:property><key>XMLRootElementNamespace</key><value/></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SequenceFlow_N</bpmn2:incoming>
    <bpmn2:outgoing>SequenceFlow_N</bpmn2:outgoing>
</bpmn2:callActivity>
```

### Message Mapping (mmap)
```xml
<bpmn2:callActivity id="CallActivity_Map" name="Map to Target">
    <bpmn2:extensionElements>
        <ifl:property><key>mappinguri</key><value>dir://mmap/src/main/resources/mapping/MyMapping.mmap</value></ifl:property>
        <ifl:property><key>mappingname</key><value>MyMapping</value></ifl:property>
        <ifl:property><key>mappingType</key><value>MessageMapping</value></ifl:property>
        <ifl:property><key>mappingReference</key><value>static</value></ifl:property>
        <ifl:property><key>mappingpath</key><value>src/main/resources/mapping/MyMapping</value></ifl:property>
        <ifl:property><key>componentVersion</key><value>1.3</value></ifl:property>
        <ifl:property><key>activityType</key><value>Mapping</value></ifl:property>
        <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::MessageMapping/version::1.3.1</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SequenceFlow_N</bpmn2:incoming>
    <bpmn2:outgoing>SequenceFlow_N</bpmn2:outgoing>
</bpmn2:callActivity>
```

### Local Integration Process (subprocess call)
```xml
<!-- Process definition -->
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

## ZIP FILE STRUCTURE (exact paths — files at root, NO wrapper folder)

```
.project
metainfo.prop
META-INF/MANIFEST.MF                                             ← LF line endings (confirmed from sample)
src/main/resources/parameters.prop
src/main/resources/parameters.propdef
src/main/resources/scenarioflows/integrationflow/MyFlow.iflw
src/main/resources/script/MyScript.groovy
src/main/resources/mapping/MyMapping.mmap                        ← graphical mapping
src/main/resources/mapping/MyMapping.xsl                         ← XSLT alternative
src/main/resources/wsdl/SourceSchema.xsd                         ← source XSD for mmap
src/main/resources/xsd/TargetSchema.xsd                          ← target XSD for mmap
src/main/resources/edmx/sap_host_port_path.edmx                  ← OData metadata (optional)
```

Shell command to package correctly (no wrapper folder):
```bash
cd /path/to/MyIFlow
zip -r ../MyIFlow.zip .project metainfo.prop META-INF/MANIFEST.MF src/
```

---

## BPMN iFlw RULES

1. All steps = `bpmn2:callActivity` except: Request Reply = `bpmn2:serviceTask`
2. Sender adapter config on `bpmn2:messageFlow` from Participant → StartEvent
3. Receiver adapter config on `bpmn2:messageFlow` from EndEvent/ServiceTask → Participant
4. Message-triggered `bpmn2:startEvent` needs `<bpmn2:messageEventDefinition/>`
5. Timer-triggered `bpmn2:startEvent` needs `<bpmn2:timerEventDefinition/>` — NOT `messageEventDefinition`
6. `bpmn2:endEvent` needs `<bpmn2:messageEventDefinition/>`
7. Script files referenced by **filename only** (no path) in `<key>script</key>`
8. **`bpmndi:BPMNDiagram` section is REQUIRED** with `name="Default Collaboration Diagram"` — without it CPI throws "unable to load"
9. All `<di:waypoint>` must have `xsi:type="dc:Point"` attribute
10. All `<bpmndi:BPMNEdge>` must have `sourceElement` and `targetElement` Shape ID references
11. Main process `cmdVariantUri` = `IntegrationProcess/version::1.2.0`; process `name` = `"Integration Process"`
12. `IFlowConfiguration/version::1.2.3` goes in collaboration extensionElements (full property set required — see CRITICAL RULES)
13. `<bpmn2:subProcess>` for error handling: NO `triggeredByEvent` attribute

---

## FILE FORMATS

### MANIFEST.MF (LF line endings — confirmed from working sample)
```
Manifest-Version: 1.0
SAP-RuntimeProfile: iflmap
Bundle-SymbolicName: MyIFlow
Bundle-Name: MyIFlow
Bundle-Version: 1.0.0
Bundle-ManifestVersion: 2
Origin-Bundle-SymbolicName: MyIFlow
SAP-NodeType: IFLMAP
Origin-Bundle-Name: MyIFlow
SAP-BundleType: IntegrationFlow

```
(blank line at end required)

### metainfo.prop (confirmed working format — description only, no bundle keys)
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

### parameters.propdef (root = `<parameters>` with `standalone="no"`)
```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?><parameters><parameter>
    <key/>
    <name>MY_PARAM</name>
    <type>xsd:string</type>
    <isRequired>true</isRequired>
    <constraint/>
    <description>Description of this parameter</description>
    <additionalMetadata/>
  </parameter><param_references><reference attribute_category="MySystem" attribute_id="ctype::Adapter/cname::HTTP/vendor::SAP/version::1.1/attrId::address" attribute_uilabel="Address" param_key="MY_PARAM"/></param_references></parameters>
```

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

---

## MMAP RULES

1. Format: `<xiObj xmlns="urn:sap-com:xi">` root — SAP XI/PI internal format
2. Source XSD in `<lnkRole role="SOURCE_IFR_MESS">`, target in `<lnkRole role="TARGET_IFR_MESS">`
3. **ALL `<viewData>` must have `y="40"`** — keeps all expressions on one row, no scrolling
4. Direct mapping: `<brick type="Dst" x="350" y="40"><arg><brick type="Src" x="50" y="40"/></arg></brick>`
5. Constant: `<brick fname="const" type="Func" x="180" y="40"><bindings><param name="value"><value>VAL</value></param></bindings></brick>`
6. Field connection lines must be drawn manually in CPI graphical mapper after import — mmap only provides the structure

---

## GROOVY SCRIPT TEMPLATE

```groovy
import com.sap.gateway.ip.core.customdev.util.Message
import java.text.SimpleDateFormat

def Message processData(Message msg) {
    def props   = msg.getProperties()
    def headers = msg.getHeaders()

    // Set unique message ID
    def msgId = "FLOW-" + UUID.randomUUID().toString().replace("-","").substring(0,12).toUpperCase()
    msg.setProperty("msgId", msgId)

    // Processing timestamp
    def sdf = new SimpleDateFormat("yyyyMMddHHmmssSSS")
    sdf.setTimeZone(TimeZone.getTimeZone("UTC"))
    msg.setProperty("processingTimestamp", sdf.format(new Date()))

    // Log to MPL attachment (only when payload logging enabled)
    def enableLog = props.get("ENABLE_PAYLOAD_LOGGING") ?: "FALSE"
    if (enableLog.toUpperCase() == "TRUE") {
        def body   = msg.getBody(String)
        def msgLog = messageLogFactory.getMessageLog(msg)
        if (msgLog != null) {
            msgLog.addAttachmentAsString("Payload", body, "application/xml")
        }
    }

    return msg
}
```

---

## HOW TO USE THIS CHEAT SHEET

Paste this entire document at the start of a new Claude chat, then say:

> "Generate an iFlow: [describe your scenario]"

**Example prompts:**
- *"Generate an iFlow: Timer triggers OData call to S4, transforms with XSLT, sends to HTTP endpoint"*
- *"Generate an iFlow: HTTPS receives JSON, converts to XML, message mapping to ORDERS05, sends via HTTP"*
- *"Generate an iFlow: HTTPS receives XML, routes via CBR, calls two OData endpoints, aggregates with Gather"*
- *"Generate an iFlow: Timer triggers every 30 min, queries changed materials from S4, sends to third party"*

**Even faster — upload your working iFlow ZIPs and say:**
> *"Use these as reference. Generate an iFlow for: [your scenario]"*

Claude will extract all versions and formats automatically from whatever you upload.

---

## TENANT INFO
- Platform: SAP Integration Suite (Cloud Integration / CPI)
- All versions tested by import + visual validation May 2026
- Sources: 7 confirmed working iFlows from live tenant
- v3 changes: Fixed ZIP packaging, metainfo.prop format, parameters.propdef root element,
  MANIFEST.MF line endings, participant ifl:type values, collaboration full property set,
  timer startEvent structure (timerEventDefinition, no extra properties),
  subProcess triggeredByEvent removal, BPMNEdge xsi:type on waypoints
