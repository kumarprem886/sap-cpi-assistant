# SAP CPI Graphical Message Mapping — Complete Reference Cheat Sheet
# Used by AI when generating .mmap files, XSDs, and mapping rules

---

## 1. ZIP BUNDLE STRUCTURE

```
mapping/<MappingName>.mmap    ← the mapping XML (REQUIRED)
wsdl/<source_xsd_name>.xsd    ← source schema (REQUIRED)
wsdl/<target_xsd_name>.xsd    ← target schema (REQUIRED, if different name)
```

**Critical rules:**
- XSDs go in `wsdl/` folder (NOT `xsd/` or root)
- .mmap goes in `mapping/` folder
- No MANIFEST.MF or .project needed for download (added by API import layer)

---

## 2. XSD FORMAT RULES FOR CPI

### ✅ CORRECT XSD (CPI-compatible):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Order">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="OrderId"       type="xs:string" minOccurs="0"/>
        <xs:element name="CustomerName"  type="xs:string" minOccurs="0"/>
        <xs:element name="OrderDate"     type="xs:string" minOccurs="0"/>
        <xs:element name="TotalAmount"   type="xs:decimal" minOccurs="0"/>
        <xs:element name="Items" minOccurs="0" maxOccurs="unbounded">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="Material"  type="xs:string" minOccurs="0"/>
              <xs:element name="Quantity"  type="xs:integer" minOccurs="0"/>
              <xs:element name="UnitPrice" type="xs:decimal" minOccurs="0"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
```

### ❌ WRONG — DO NOT USE in generated XSDs:
- `targetNamespace` attribute → breaks CPI path resolution
- `xmlns:tns` prefix references → avoid
- `elementFormDefault="qualified"` with targetNamespace → incompatible
- Deep nesting (more than 4 levels) → keep flat when possible
- `xsi:nil="true"` attributes → avoid in XSD definitions

### XSD Design Guidelines:
- Root element: singular noun, CamelCase (Product, Order, Material, Delivery)
- Field names: CamelCase for OData-style (MaterialNumber, OrderDate, CustomerName)
- Field names: UPPER_CASE for IDoc-style (MATNR, WERKS, BUDAT)
- Max recommended nesting: 3-4 levels
- Use `minOccurs="0"` on most elements for flexibility
- Use `maxOccurs="unbounded"` for repeating elements (line items)
- Types: xs:string for most, xs:decimal for amounts, xs:integer for quantities
- DO NOT add targetNamespace — CPI handles namespaces internally

---

## 3. .MMAP XML STRUCTURE (urn:sap-com:xi format)

```xml
<?xml version="1.0" encoding="utf-8"?>
<xiObj xmlns="urn:sap-com:xi">
  <idInfo VID="01">
    <vc caption="LOCAL" sp="-1" swcGuid="00000000000000000000000000000000" vcType="S">
      <clCxt consider="A"/>
    </vc>
    <key typeID="XI_TRAFO" version=""/>
    <version>1.0</version>
  </idInfo>
  <documentation><description/></documentation>
  <generic>
    <admInf>
      <modifBy></modifBy><modifAt></modifAt>
      <modifAtLong>TIMESTAMP_MS</modifAtLong>
      <owner/>
    </admInf>
    <lnks>
      <!-- TARGET comes FIRST -->
      <lnkRole kpos="1" role="TARGET_IFR_MESS">
        <lnk rMode="R">
          <key typeID="xsd" version="1.1">
            <elem>target.xsd</elem>              ← XSD filename
            <elem>src/main/resources/wsdl</elem>  ← always this path
            <elem>RootElementName</elem>           ← MUST match xs:element name in XSD
          </key>
        </lnk>
      </lnkRole>
      <!-- SOURCE comes SECOND -->
      <lnkRole kpos="1" role="SOURCE_IFR_MESS">
        <lnk rMode="R">
          <key typeID="xsd" version="1.1">
            <elem>source.xsd</elem>
            <elem>src/main/resources/wsdl</elem>
            <elem>RootElementName</elem>           ← MUST match xs:element name in XSD
          </key>
        </lnk>
      </lnkRole>
    </lnks>
  </generic>
  <content>
    <tr:XiTrafo xmlns:tr="urn:sap-com:xi:mapping:xitrafo">
      <tr:MetaData>
        <mappingtool version="XI7.1">
          <project version="XI7.1">
            <!-- libstorage section (always same) -->
            <transformation>
              <!-- ALL MAPPING BRICKS GO HERE -->
              BRICK_XML_HERE
            </transformation>
          </project>
        </mappingtool>
      </tr:MetaData>
      <tr:ByteCodeJar/>
      <tr:SourceStructure/><tr:TargetStructure/>
      <tr:Multiplicity>1:1</tr:Multiplicity>
    </tr:XiTrafo>
  </content>
</xiObj>
```

---

## 4. BRICK XML FORMAT (confirmed from real CPI exports)

### Direct mapping (source → target, no transformation):
```xml
<brick gid="0" path="/Target/Root/FieldName" type="Dst">
  <viewData x="200" y="40"/>
  <arg>
    <brick gid="0" path="/Source/Root/FieldName" type="Src">
      <viewData x="50" y="40"/>
    </brick>
  </arg>
  <group/>
</brick>
```

### Function brick (transformation):
```xml
<brick gid="0" path="/Target/Root/Field" type="Dst">
  <viewData x="200" y="40"/>
  <arg>
    <brick fname="FUNCTION_NAME" fns="dflt" type="Func">
      <viewData x="125" y="30"/>
      <arg>
        <brick gid="0" path="/Source/Root/Field" type="Src">
          <viewData x="50" y="30"/>
        </brick>
      </arg>
      <bindings>
        <param name="PARAM_NAME"><value>PARAM_VALUE</value></param>
      </bindings>
    </brick>
  </arg>
  <group/>
</brick>
```

### Multi-arg function (concat example):
```xml
<brick fname="concat" fns="dflt" type="Func">
  <viewData x="125" y="30"/>
  <arg>
    <brick gid="0" path="/Source/DateField" type="Src"><viewData x="50" y="30"/></brick>
  </arg>
  <arg pin="1">
    <brick gid="0" path="/Source/TimeField" type="Src"><viewData x="50" y="60"/></brick>
  </arg>
  <bindings><param name="delimeter"><value>T</value></param></bindings>
</brick>
```

**Key rules:**
- Function bricks use `fname` + `fns="dflt"` + `type="Func"` (NOT funcName/type=Function)
- First arg: `<arg>` (no pin attribute)
- Subsequent args: `<arg pin="1">`, `<arg pin="2">` etc.
- Parameters go in `<bindings>` not as separate arg bricks

---

## 5. ALL NODE FUNCTIONS — CORRECT fname VALUES

### STRING FUNCTIONS
| User writes | fname in XML | Bindings |
|-------------|--------------|---------|
| toUpperCase((/field)) | toUpperCase | none |
| toLowerCase((/field)) | toLowerCase | none |
| trim((/field)) | trim | none |
| length((/field)) | length | none |
| substring((/f), 0, 5) | substring | from=0, to=5 |
| (/f1)+SEP+(/f2) | concat | delimeter=SEP |
| replaceAll((/f), old, new) | replaceString | search=old, replace=new |
| SplitByValue((/f), ,) | SplitByValue | delimeter=, |
| indexOf((/f), text) | indexOf | search=text |
| lastIndexOf((/f), text) | lastIndexOf | search=text |
| endsWith((/f), suffix) | endsWith | value=suffix |
| startsWith((/f), prefix) | startsWith | value=prefix |
| equalsS((/f), val) | equalsS | (second arg) |
| compare((/f1), (/f2)) | compare | (two args) |
| contains((/f), text) | contains | search=text |
| copyValue((/f)) | copyValue | none |

### DATE FUNCTIONS
| User writes | fname in XML | Bindings |
|-------------|--------------|---------|
| formatDate((/f), yyyyMMdd, yyyy-MM-dd) | **TransformDate** | iform=yyyyMMdd, oform=yyyy-MM-dd, calend=... |
| currentDate() | currentDate | none (no source arg) |
| DateBefore((/d1), (/d2)) | DateBefore | (two args) |
| DateAfter((/d1), (/d2)) | DateAfter | (two args) |

**IMPORTANT:** `formatDate` is a user alias → real fname is `TransformDate`

### ARITHMETIC
| User writes | fname | Note |
|-------------|-------|------|
| add((/f1), (/f2)) | add | two source args |
| subtract((/f1), (/f2)) | subtract | |
| multiply((/f1), (/f2)) | multiply | |
| divide((/f1), (/f2)) | divide | |
| abs((/f)) | abs | single arg |
| neg((/f)) | neg | single arg |
| round((/f)) | round | single arg |
| ceil((/f)) | ceil | single arg |
| floor((/f)) | floor | single arg |
| max((/f1), (/f2)) | max | two args |
| min((/f1), (/f2)) | min | two args |
| FormatNum((/f), 0.00) | FormatNum | format=0.00 |

### BOOLEAN / CONDITIONAL
| User writes | fname | Note |
|-------------|-------|------|
| if((/cond), yes, no) | if | three args |
| ifWithoutElse((/c), val) | ifWithoutElse | |
| equals((/f), VALUE) | **Equals** | capital E |
| notEquals((/f), VALUE) | notEquals | |
| Not((/bool)) | Not | single arg |
| And((/b1), (/b2)) | And | two args |
| Or((/b1), (/b2)) | Or | two args |

**IMPORTANT:** `equals` → real fname is `Equals` (capital E)

### NODE / CONTEXT FUNCTIONS
| User writes | fname | Note |
|-------------|-------|------|
| useOneAsMany((/f)) | useOneAsMany | |
| SplitByValue((/f), ,) | **SplitByValue** | capital S, delimeter binding |
| mapWithDefault((/f), val) | mapWithDefault | default_value binding |
| exists((/f)) | exists | boolean result |
| removeContexts((/f)) | removeContexts | |
| collapseContexts((/f)) | collapseContexts | |
| createIf((/cond)) | createIf | |
| sort((/f)) | sort | order=ascending |
| sortByKey((/f)) | sortByKey | |

**IMPORTANT:** `splitByValue` user alias → real fname is `SplitByValue` (capital S)

---

## 6. PATH FORMAT RULES

- Paths start with `/RootElement/Parent/Child`
- Root element = the `name` attribute of the top-level `xs:element` in XSD
- **NO namespace prefixes** in paths, even for namespaced XSDs
- Only leaf fields (no children) should be mapped as Src/Dst fields
- Container elements can be mapped for structure linking (useOneAsMany etc.)

### Example paths:
```
Source XSD root "msg":    /msg/header/date, /msg/body/stockreport/ln/mn
Target XSD root "Header": /Header/HeaderType/RunDate, /Header/HeaderType/to_Stock/StockType/MaterialNumber
IDoc MATMAS05:            /MATMAS05/IDOC/E1MARAM/MATNR, /MATMAS05/IDOC/E1MARAM/MEINS
OData A_Product:          /A_Product/Product/MaterialNumber, /A_Product/Product/BaseUnit
```

---

## 7. COMMON INTEGRATION PATTERNS

### IDoc → OData Mappings
| IDoc Field | OData Field | Rule |
|-----------|-------------|------|
| MATNR | MaterialNumber | direct |
| MEINS | BaseUnit | toUpperCase |
| MAKTX | ProductDescription | direct |
| ERSDA | CreationDate | formatDate(yyyyMMdd→yyyy-MM-dd) |
| MTART | MaterialType | direct |
| WERKS | Plant | direct |
| LGORT | StorageLocation | direct |
| BUKRS | CompanyCode | direct |
| KOSTL | CostCenter | direct |
| BWART | MovementType | direct |
| MENGE | Quantity | direct |

### Date Format Patterns
| Pattern | Meaning | Example |
|---------|---------|---------|
| yyyyMMdd | YYYYMMDD → no separators | 20240101 |
| yyyy-MM-dd | ISO date | 2024-01-01 |
| dd.MM.yyyy | German format | 01.01.2024 |
| HHmmss | Time no separators | 143022 |
| HH:mm:ss | Time with separators | 14:30:22 |
| yyyyMMddHHmmss | DateTime combined | 20240101143022 |

### Concat Patterns
| Goal | Expression |
|------|-----------|
| Date + T + Time | (/date)+T+(/time) |
| Plant + _ + Location | (/Plant)+_+(/Location) |
| First + Space + Last | (/FirstName)+ +(/LastName) |
| CompCode + - + CostCenter | (/CompCode)+-+(/CostCenter) |

---

## 8. SAP CPI VERSION & API INFO

- CPI API version: OData v2, path: /api/v1/
- Message Mapping artifact: MessageMappingDesigntimeArtifacts
- iFlow artifact: IntegrationDesigntimeArtifacts
- Value Mapping: ValueMappingDesigntimeArtifacts
- Script Collection: ScriptCollectionDesigntimeArtifacts
- Deploy: DeployMessageMappingDesigntimeArtifact?Id='ID'&Version='active'
- .mmap namespace: urn:sap-com:xi
- XiTrafo namespace: urn:sap-com:xi:mapping:xitrafo
- Mapping tool version: XI7.1 (use this in generated mmaps)

---

## 9. GENERATION RULES (AI MUST FOLLOW)

1. **Never add targetNamespace to generated XSDs** — causes path resolution failure
2. **Root element name in lnk MUST exactly match** the xs:element name in the XSD
3. **All paths must start with /RootElementName/** matching the XSD
4. **Use real fname values** (TransformDate not formatDate, Equals not equals, SplitByValue not splitbyvalue)
5. **Separators in concat go in delimeter binding** not as a third arg brick
6. **Date functions need calend binding** along with iform/oform
7. **Map container elements** (parent nodes) as well as leaf fields for proper structure
8. **Keep XSDs flat and simple** — avoid targetNamespace, avoid complex type references
9. **Use minOccurs="0"** on most elements for flexibility
10. **Test path consistency** — every path in <arg> bricks must exist in the XSD
