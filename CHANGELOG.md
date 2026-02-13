## [1.1.0](https://github.com/f6ra07nk14/structcast/compare/v1.0.0...v1.1.0) (2026-02-13)


### 👷 Build

* add git installation to Dockerfile for development environment ([9587b87](https://github.com/f6ra07nk14/structcast/commit/9587b87eb3644d04b3a355069073c3fa62118291))
* remove Node.js installation and dependencies from Dockerfile ([1969b6d](https://github.com/f6ra07nk14/structcast/commit/1969b6d72c255f41959d91294f3edc865297b8ad))
* remove unsupported Python version 3.8 from the versions list ([71f177c](https://github.com/f6ra07nk14/structcast/commit/71f177c692b255cea297c0034c1193273e302865))
* upgrade dependency packages ([8060c26](https://github.com/f6ra07nk14/structcast/commit/8060c263cae0f878d7f4bb2fbb1d43e19d0d72c2))


### 📦 Other

* **release:** 1.1.0 [skip ci] ([c6fcdcb](https://github.com/f6ra07nk14/structcast/commit/c6fcdcb6d479f2c05ec284ae951d94299f7db87f)), closes [#10](https://github.com/f6ra07nk14/structcast/issues/10) [#12](https://github.com/f6ra07nk14/structcast/issues/12) [#12](https://github.com/f6ra07nk14/structcast/issues/12) [#11](https://github.com/f6ra07nk14/structcast/issues/11) [#13](https://github.com/f6ra07nk14/structcast/issues/13) [#6](https://github.com/f6ra07nk14/structcast/issues/6) [#7](https://github.com/f6ra07nk14/structcast/issues/7) [#9](https://github.com/f6ra07nk14/structcast/issues/9) [#8](https://github.com/f6ra07nk14/structcast/issues/8) [#10](https://github.com/f6ra07nk14/structcast/issues/10) [#12](https://github.com/f6ra07nk14/structcast/issues/12) [#12](https://github.com/f6ra07nk14/structcast/issues/12) [#11](https://github.com/f6ra07nk14/structcast/issues/11) [#13](https://github.com/f6ra07nk14/structcast/issues/13) [#6](https://github.com/f6ra07nk14/structcast/issues/6) [#7](https://github.com/f6ra07nk14/structcast/issues/7) [#9](https://github.com/f6ra07nk14/structcast/issues/9) [#8](https://github.com/f6ra07nk14/structcast/issues/8) [#10](https://github.com/f6ra07nk14/structcast/issues/10)
* **release:** 1.1.0 [skip ci] ([4dc5a20](https://github.com/f6ra07nk14/structcast/commit/4dc5a2072b145c44a17b12dd3193c61245f27c19)), closes [#10](https://github.com/f6ra07nk14/structcast/issues/10) [#12](https://github.com/f6ra07nk14/structcast/issues/12) [#12](https://github.com/f6ra07nk14/structcast/issues/12) [#11](https://github.com/f6ra07nk14/structcast/issues/11) [#13](https://github.com/f6ra07nk14/structcast/issues/13) [#6](https://github.com/f6ra07nk14/structcast/issues/6) [#7](https://github.com/f6ra07nk14/structcast/issues/7) [#9](https://github.com/f6ra07nk14/structcast/issues/9) [#8](https://github.com/f6ra07nk14/structcast/issues/8)
* **release:** 1.1.0 [skip ci] ([bc51251](https://github.com/f6ra07nk14/structcast/commit/bc512512b11ca5a9f4941720d8ca03b684380437)), closes [#10](https://github.com/f6ra07nk14/structcast/issues/10) [#12](https://github.com/f6ra07nk14/structcast/issues/12) [#12](https://github.com/f6ra07nk14/structcast/issues/12) [#11](https://github.com/f6ra07nk14/structcast/issues/11) [#13](https://github.com/f6ra07nk14/structcast/issues/13) [#6](https://github.com/f6ra07nk14/structcast/issues/6) [#7](https://github.com/f6ra07nk14/structcast/issues/7) [#9](https://github.com/f6ra07nk14/structcast/issues/9) [#8](https://github.com/f6ra07nk14/structcast/issues/8)
* update uv.lock to sync with pyproject.toml version ([cd00b27](https://github.com/f6ra07nk14/structcast/commit/cd00b27afcb4c9c379e07bdaa3fc7102727b05b4))


### 🦊 CI/CD

* add job to publish wheel file to TestPyPI after successful release ([20ec1b9](https://github.com/f6ra07nk14/structcast/commit/20ec1b93c79c076633eea9cc2ed530951cd29687))
* add safe.directory configuration for GitHub Actions ([a13c5df](https://github.com/f6ra07nk14/structcast/commit/a13c5df35fe878a37f546e35420f4962cd09de61))
* change release type for CI changes to patch ([c401add](https://github.com/f6ra07nk14/structcast/commit/c401addc73e759bef03aa1d8d0af12e308855e46))
* enhance Docker image existence check with manifest details ([50bde38](https://github.com/f6ra07nk14/structcast/commit/50bde38796d729de82924af4d8245e03187a9e26))
* prevent CI changes from triggering a release ([0368fe5](https://github.com/f6ra07nk14/structcast/commit/0368fe5cfbb97d1e6ba8b2c93519bb3210df833d))
* publish job to deploy to PyPI instead of TestPyPI ([5980a96](https://github.com/f6ra07nk14/structcast/commit/5980a968f5f12d880ecc727ac4994542c31baf98))
* refactor Docker image handling and remove unused cleanup job ([c981272](https://github.com/f6ra07nk14/structcast/commit/c981272a9000cb904a43194b1c557303d8074eb9))
* remove redundant environment declaration from release job ([cdb5686](https://github.com/f6ra07nk14/structcast/commit/cdb56868053e1ef4019b09d5452e19124bc3a7cf))
* restore conditions for publish-to-pypi job to ensure proper execution ([46661ce](https://github.com/f6ra07nk14/structcast/commit/46661cedbca84b567514be96918d55d9d0573583))
* simplify condition for publishing to TestPyPI ([b13b76c](https://github.com/f6ra07nk14/structcast/commit/b13b76c8752356600e1c9a76474ee5850e2d0aa3))
* standardize environment name for TestPyPI job ([a2d6f99](https://github.com/f6ra07nk14/structcast/commit/a2d6f991b3b2d41f036aa11f96bb2ae6b193b8d1))
* update actions/checkout to v6 and remove package.json ([24d8d4b](https://github.com/f6ra07nk14/structcast/commit/24d8d4b97b6ce8e6eafcded3a5b61affdbf5a960))
* update Docker image caching strategy and refine cleanup logic for merged PRs ([dcb7189](https://github.com/f6ra07nk14/structcast/commit/dcb71897f9203ed519bc7b14435c4df261efa6c0))
* update publish-to-pypi job conditions for better flexibility ([9e353ff](https://github.com/f6ra07nk14/structcast/commit/9e353ff78f1129b25cac13a66c6f61a1789e929b))
* update release job dependencies and permissions; add Node.js installation to Dockerfile ([7067276](https://github.com/f6ra07nk14/structcast/commit/70672760cb100fc1b084028a53cd6d27871b7e77))
* update release preparation command and include uv.lock in assets ([097d7f4](https://github.com/f6ra07nk14/structcast/commit/097d7f47ad6bcd9c192ce3f436b8094297230bd7))
* update semantic-release setup to install dependencies and streamline execution ([7f3e8a9](https://github.com/f6ra07nk14/structcast/commit/7f3e8a9af85106d1ca1580006960a6f89060feac))
* update semantic-release setup to use actions/setup-node and install dependencies ([d3a8b48](https://github.com/f6ra07nk14/structcast/commit/d3a8b48f2095a6b875ba7f15685662b751176bb2))
* update semantic-release setup to use cycjimmy/semantic-release-action and streamline configuration ([ea84682](https://github.com/f6ra07nk14/structcast/commit/ea84682ba76a52aa5ce3e50742d286611ff35424))
* use pre-installed semantic-release instead of npx ([#10](https://github.com/f6ra07nk14/structcast/issues/10)) ([ab86cc3](https://github.com/f6ra07nk14/structcast/commit/ab86cc3638fc229cb3438f1969d6402f41f77121))


### 📔 Docs

* remove outdated usage guidelines and debugging tips from SKILL.md ([6cfab00](https://github.com/f6ra07nk14/structcast/commit/6cfab00bf3e426f68aa9ad31c68f7821e672b495))
* update SKILL.md to enhance description and add usage examples ([48eff50](https://github.com/f6ra07nk14/structcast/commit/48eff505552fb6c14046bdc34dd27f9f00ff8ab3))


### 💎 Features

* add custom pattern registration and validation tests ([dd24383](https://github.com/f6ra07nk14/structcast/commit/dd243831e4b1057d40a53df69a015644c5987df1))


### 🔧 Fixes

* change Docker cache strategy to prevent untagged images ([6951228](https://github.com/f6ra07nk14/structcast/commit/6951228f1dc22480eec1325933bb61467e422ca8))
* update CHANGELOG for version 1.1.0 release, and retry ci ([17d0f77](https://github.com/f6ra07nk14/structcast/commit/17d0f770ce5672c349cf14b3aeb10cc3eb941e30))


### 🔨 Refactor

* remove redundant manifest information extraction from CI workflow ([0ecafcc](https://github.com/f6ra07nk14/structcast/commit/0ecafcc0d451a448b4215132f9bba3a4c9c236c0))


### ✨ Style

* add type ignore for validation in ObjectPattern ([64d5122](https://github.com/f6ra07nk14/structcast/commit/64d5122ae2296c3e3d4025e80a9ba64523cdea51))

## 1.0.0 (2026-02-08)


### 👷 Build

* add tox configuration for testing and linting environments ([9818319](https://github.com/f6ra07nk14/structcast/commit/981831946423c05e268642b1630fea34d39aefe0))
* add Tox configuration for testing and linting environments ([93480dd](https://github.com/f6ra07nk14/structcast/commit/93480dd7ca70a6201101eea42f334ef68e923028))
* initialize StructCast project with initial metadata and README ([1b658ea](https://github.com/f6ra07nk14/structcast/commit/1b658ea2333c1834eba9af549faca87ae6893108))
* set HOME environment variable to /app in Dockerfile ([ee3c6fd](https://github.com/f6ra07nk14/structcast/commit/ee3c6fdd9cf328d29dfe0de964a591b4714d150f))
* simplify pydantic environment list and update pytest command options ([992e644](https://github.com/f6ra07nk14/structcast/commit/992e64449e580455afe9cea59b7b749b8e5201a6))
* update Dockerfile to support multiple Python versions and non-root user ([cf57cf3](https://github.com/f6ra07nk14/structcast/commit/cf57cf3e6e7621d12d8f571bdb652547a2a657f3))
* update pyproject.toml to include dependencies and configuration for development tools ([5d272a1](https://github.com/f6ra07nk14/structcast/commit/5d272a11e1f1f10f98b3812923217e8f80fb2118))
* update pyproject.toml to use 'editable' package for environment setup ([7cabdaf](https://github.com/f6ra07nk14/structcast/commit/7cabdaf5d5f59ba172257ca5da6d79a6a9861dc4))
* upgrade dependency packages ([be495b2](https://github.com/f6ra07nk14/structcast/commit/be495b2ff271fdce09e3313807174da88382bb6e))


### 📦 Other

* add .python-version to .gitignore for environment management ([58e227e](https://github.com/f6ra07nk14/structcast/commit/58e227ea743066e3a46436819c1777aa4352edf1))
* enable no_site_packages option in mypy configuration ([56cfd84](https://github.com/f6ra07nk14/structcast/commit/56cfd8427e8984c2ba55bdc7e43fd0a1f1531058))


### 🦊 CI/CD

* configure UV cache directory and update Dockerfile mounts for tox ([49c3fa8](https://github.com/f6ra07nk14/structcast/commit/49c3fa8b9fb31936dbc655de15a438780964826d))
* disable fail-fast strategy in CI configuration for better stability ([6efd935](https://github.com/f6ra07nk14/structcast/commit/6efd935fb80a1714f48e1c8a31a34abe3c1a4e80))
* enhance CI configuration to support multiple Python versions and improve image tagging ([f6aa420](https://github.com/f6ra07nk14/structcast/commit/f6aa420df867c44a98e64640c6e1c2f9f448c125))
* enhance Docker setup conditions for improved build efficiency ([a9318e9](https://github.com/f6ra07nk14/structcast/commit/a9318e9615327773973a060bf9426581a1b6f3b7))
* improve test workflow by separating type checking and simplifying test command ([7416df9](https://github.com/f6ra07nk14/structcast/commit/7416df9c31469c2486791f84da4a96e38b14b29b))
* refactor Docker build logic and improve image tagging for CI workflow ([60b73a1](https://github.com/f6ra07nk14/structcast/commit/60b73a1db0b00f7c4210b6d30be18ac1a6d9e4eb))
* remove '-latest' suffix from Docker image tags for consistency ([1742faa](https://github.com/f6ra07nk14/structcast/commit/1742faa7479c61bc3de6a6c66987b2c45bd3cceb))
* simplify Docker image tagging and update test execution to use Tox for all environments ([6915d27](https://github.com/f6ra07nk14/structcast/commit/6915d2734af96e5d0a4c08011a08bebe1a56c8c6))
* update Docker file checks in CI configuration ([d7a7db4](https://github.com/f6ra07nk14/structcast/commit/d7a7db4be5f1b1485c546aae36defe8c0a7f58b3))
* update image tag format for Docker verification step ([6c4021b](https://github.com/f6ra07nk14/structcast/commit/6c4021bc4931d3989f610273d5d0cbe535a527f6))
* update versioning commands and include additional asset for release ([cfeb12d](https://github.com/f6ra07nk14/structcast/commit/cfeb12df32b66f471ec4b3271ba9c21f8496091c))


### 📔 Docs

* add AI Agent Resources section to README and create README_AGENT.md for AI coding agents ([eea6a64](https://github.com/f6ra07nk14/structcast/commit/eea6a6415704308890a5018bd896bf2cb621b793))
* add development guide for StructCast with copilot interaction policy ([a158996](https://github.com/f6ra07nk14/structcast/commit/a158996c55079e476b5606d507f860103fcf9be8))
* add docstrings for constants in constants.py for clarity ([f657707](https://github.com/f6ra07nk14/structcast/commit/f6577070e9403571274f575fe3fee2f725d0741f))
* enhance docstrings for specification models to clarify input handling ([4f59ed3](https://github.com/f6ra07nk14/structcast/commit/4f59ed3220bd1441345a0cbd06f284fcda008a45))
* enhance README with detailed explanations of StructCast features and advanced patterns ([653861a](https://github.com/f6ra07nk14/structcast/commit/653861a34d75e12e8722140d1dec367e616df871))
* expand copilot instructions with detailed architecture, patterns, conventions, and development workflow ([6b5aa16](https://github.com/f6ra07nk14/structcast/commit/6b5aa166a2bc6c7e9d54d531c8073ca469f01266))
* update README to enhance clarity and detail on library features and usage ([9040a4d](https://github.com/f6ra07nk14/structcast/commit/9040a4d6db827a5e2015675ddde45ed79f210f63))
* update return type annotation for load_yaml function to specify loaded data type ([2f1eb8a](https://github.com/f6ra07nk14/structcast/commit/2f1eb8a7842d6cb88142d09d427089bbfcce69b2))


### 💎 Features

* add _casting function to apply a series of callable transformations using unroll_call ([8a3de3d](https://github.com/f6ra07nk14/structcast/commit/8a3de3daff62e28cc2470a34c401cfbe56294789))
* add checks for protected and private members in import function ([7528180](https://github.com/f6ra07nk14/structcast/commit/75281808cc6d227b3150de06874799d6ec49c1e3))
* add dataclass utilities with enhanced kw_only and slots support for Python 3.10+ ([ab4012f](https://github.com/f6ra07nk14/structcast/commit/ab4012f0b3def8e6f083f8a42536c7585c91cd5b))
* add default settings for security checks in constants and update SecuritySettings class ([2f121e4](https://github.com/f6ra07nk14/structcast/commit/2f121e4b45da657aa37b337f70f85c318f6312be))
* add dump_yaml function for YAML string serialization and enhance existing dump_yaml method with additional parameters ([d7a98e1](https://github.com/f6ra07nk14/structcast/commit/d7a98e10c7956f1b19d33d013750f0bc29e5a642))
* add instantiation patterns for dynamic object creation and manipulation ([51d3117](https://github.com/f6ra07nk14/structcast/commit/51d3117840c9d1418712860989b32156b8e4e21b))
* add load_yaml_from_stream function and refactor YAML loading methods ([e35ba6e](https://github.com/f6ra07nk14/structcast/commit/e35ba6e9acca27a6337d34d1ccbf24d04cbd6008))
* add model serialization and caching for patterns in instantiator ([b432462](https://github.com/f6ra07nk14/structcast/commit/b432462d5ec87f407a08da650d2c9bd3619c1c36))
* add model serialization method to instantiator ([9ebdfb5](https://github.com/f6ra07nk14/structcast/commit/9ebdfb5a1fe8ee28ecce6642780f871fb3405ea6))
* add model validators for AddressPattern, CallPattern, and ObjectPattern classes ([5b12e1f](https://github.com/f6ra07nk14/structcast/commit/5b12e1f0511a276083d8635e37fef3c9c7c89f1d))
* add overloaded check_elements function for flexible element validation ([bc4c8e7](https://github.com/f6ra07nk14/structcast/commit/bc4c8e7a07028d4913b023b41f952f40d51d6c84))
* add placeholder resolver and processing function ([2c08323](https://github.com/f6ra07nk14/structcast/commit/2c083230b4a12e6cc7f1132d984f3123ed5b3988))
* add register_accesser function to allow custom data accessers registration ([0fddf46](https://github.com/f6ra07nk14/structcast/commit/0fddf46dd8796ffcb6ba51ef8f1a21c70423ea3d))
* add ruamel-yaml dependency for enhanced YAML support ([7933779](https://github.com/f6ra07nk14/structcast/commit/7933779b61bd589f112bcb013408377dcb6aba9e))
* add skip specification ([4e7f1af](https://github.com/f6ra07nk14/structcast/commit/4e7f1afe6d8795dbe0272387e6284322a3e89431))
* add specification conversion module with resolver registration ([50bc8d4](https://github.com/f6ra07nk14/structcast/commit/50bc8d4758d1c7b9258b11087f4e9b8d455ba0fd))
* add structured specification conversion and construction functions ([f400b10](https://github.com/f6ra07nk14/structcast/commit/f400b101a4966595a28aa101eaef1a65fef5c6c3))
* add timeout checks for instantiation process to enhance security ([bd875c1](https://github.com/f6ra07nk14/structcast/commit/bd875c13bf01d7c5b26c80b63478156bfd671b55))
* add typing-extensions dependency for improved type hinting support ([74bb723](https://github.com/f6ra07nk14/structcast/commit/74bb723ce355f0f9f75b7e253c0a18b1b0f00eb6))
* add unroll_call function to handle callable unpacking ([a9b7f30](https://github.com/f6ra07nk14/structcast/commit/a9b7f301ec4ad88190cc15f91038c758eb8717a9))
* add utility functions for importing modules and loading YAML files ([d29a248](https://github.com/f6ra07nk14/structcast/commit/d29a24836ef6f78313bbb92fa965f73b59b40201))
* add YAML loading functionality with ruamel.yaml support ([b01fc7c](https://github.com/f6ra07nk14/structcast/commit/b01fc7c725b22aec9e644232fe4878aea4907c2d))
* enhance Jinja template support with new validation and structure extension ([bf5ae35](https://github.com/f6ra07nk14/structcast/commit/bf5ae35f4676925df538395487748be19b9afbe4))
* enhance model validation and serialization with new field serializers and validation methods ([3601df5](https://github.com/f6ra07nk14/structcast/commit/3601df5f6932e60f6433482559f39b222077a70f))
* enhance pyproject.toml with license, authors, keywords, classifiers, and project URLs ([a27618b](https://github.com/f6ra07nk14/structcast/commit/a27618bf79dee90e6bc5ab3f9d5579a24fa6cbee))
* enhance security configuration with allowed modules and context manager for tests ([5c29786](https://github.com/f6ra07nk14/structcast/commit/5c29786d4b1455c2a1117d36b49ccd3dc480607d))
* enhance security settings by adding support for dangerous dunder methods and improving path validation ([d64ab19](https://github.com/f6ra07nk14/structcast/commit/d64ab19f11e01c924dd3b6d5517c64bb5546fad4))
* enhance specification handling with new access and construct functions ([613c176](https://github.com/f6ra07nk14/structcast/commit/613c176e21ae88d445c7e241e4f930813347357e))
* enhance specification handling with new SpecIntermediate class and flexible constructors ([6da842c](https://github.com/f6ra07nk14/structcast/commit/6da842c058cef706467c899daf78bb4fca8bfadd))
* enhance validation methods to support additional spec types and BaseModel integration ([6fec8a2](https://github.com/f6ra07nk14/structcast/commit/6fec8a223b13fef05bb3492e8cc07a173d361979))
* enhance YAML manager with new dump functionality and refactor security settings usage ([e3a6552](https://github.com/f6ra07nk14/structcast/commit/e3a655212ca6b7414a2fbb12e0d7dc1461758c4b))
* enhance YAML manager with optional instance parameter for load and dump methods ([cf20070](https://github.com/f6ra07nk14/structcast/commit/cf20070f363ab6d76b48064f3b95bea4a896806d))
* expand DEFAULT_ALLOWED_MODULES and DEFAULT_ALLOWED_BUILTINS for enhanced safety and functionality ([c5a4fd4](https://github.com/f6ra07nk14/structcast/commit/c5a4fd4c0ec52b223da72cd4e755e2d0954476fe))
* implement recursion depth checks in instantiation process for enhanced security ([1133fba](https://github.com/f6ra07nk14/structcast/commit/1133fbac50eb0ae4e74bfa02cc47e2ac4cad2a60))
* implement split_attribute function for improved attribute path handling ([dee47c1](https://github.com/f6ra07nk14/structcast/commit/dee47c103dffa4043e183f57cbd8c5a66546c511))
* implement WithPipe model for casting functions and refactor _Constructor to inherit from it ([b482d51](https://github.com/f6ra07nk14/structcast/commit/b482d51d2439b4307f36430cc1d8540a63a59345))
* implement YAML manager for enhanced YAML handling and serialization ([ee307a6](https://github.com/f6ra07nk14/structcast/commit/ee307a6e2df4f6fd6dbb05faf8e956a58a517305))
* introduce SPEC_PREFIX constant for improved specification handling ([5737e7b](https://github.com/f6ra07nk14/structcast/commit/5737e7b3ada2327e878952497d07a6c25e84a644))
* refactor security utilities and settings for improved path resolution and checks ([0baa6b6](https://github.com/f6ra07nk14/structcast/commit/0baa6b6b03f9e0741d903e25133d369d54f07897))
* update README with advanced examples and installation instructions ([a28e3a4](https://github.com/f6ra07nk14/structcast/commit/a28e3a4ff294570cc5460f79a5f92c1ff4fc4239))
* update ruamel-yaml dependency to include jinja2 support ([8739e26](https://github.com/f6ra07nk14/structcast/commit/8739e26fe6a370641c1dcbb96141d77e1df3fc0d))


### 🔧 Fixes

* add 'math' to DEFAULT_ALLOWED_MODULES for enhanced functionality ([0b3a17e](https://github.com/f6ra07nk14/structcast/commit/0b3a17eb08e02cecef43fb1f86b9c4ac6d27e428))
* change debug log to warning for unsupported type in specification construction ([17a424a](https://github.com/f6ra07nk14/structcast/commit/17a424a7cfe8029a5edef293f576a372d48b528f))
* **ci:** fix container image context and remove Python 3.14 support ([#1](https://github.com/f6ra07nk14/structcast/issues/1)) ([b741c92](https://github.com/f6ra07nk14/structcast/commit/b741c92f3d77a27fc06d5f1f976ce91132455612))
* correct dump_yaml function to handle file streams and improve YAML serialization ([248af12](https://github.com/f6ra07nk14/structcast/commit/248af126ae0306916a36a30f714cc07de4af9efc))
* enhance raw validation in AddressPattern, CallPattern, and ObjectPattern classes ([e2f2fc3](https://github.com/f6ra07nk14/structcast/commit/e2f2fc3d4c75dad7b62b236518cdfc048b6e1fec))
* fix CI errors and optimize Docker build for package reuse ([#2](https://github.com/f6ra07nk14/structcast/issues/2)) ([612ae17](https://github.com/f6ra07nk14/structcast/commit/612ae1720505da231a3dce2e15f9f7b1fc23ff04))
* improve error handling in ObjectPattern build method with validation feedback ([4092a9a](https://github.com/f6ra07nk14/structcast/commit/4092a9a4656e32f8ca0adf231c4581be4f178cec))
* remove abstractmethod decorator and improve type checks in Jinja template processing ([f70928e](https://github.com/f6ra07nk14/structcast/commit/f70928e08cb97c2bd156b4c28e00ad1152702835))
* remove risky attribute for each module ([ab5bef9](https://github.com/f6ra07nk14/structcast/commit/ab5bef960be383c88966752e3e76fde098bbd01d))
* remove unnecessary isinstance checks for BaseModel in raw validation methods ([de099d4](https://github.com/f6ra07nk14/structcast/commit/de099d4bd14d816e3f672db24639077b1d7cf526))
* remove unnecessary Sequence check in instantiator type validation ([87a2dc4](https://github.com/f6ra07nk14/structcast/commit/87a2dc42ce21ecfc6f87623cc50406c06ee0edd3))
* replace isinstance check with type check for dict in instantiator ([d09db7f](https://github.com/f6ra07nk14/structcast/commit/d09db7f350313410693b570cf4c34bbe5e898e33))
* replace isinstance check with type check for dict in specifier module ([b802e47](https://github.com/f6ra07nk14/structcast/commit/b802e47ff07947c4237a865ac3821f372e18b70a))
* Set HOME=$(pwd) in workflow to satisfy strict path security check ([#4](https://github.com/f6ra07nk14/structcast/issues/4)) ([11ed65c](https://github.com/f6ra07nk14/structcast/commit/11ed65caf81bb9786d5d12f18f8dc621bb85f9df)), closes [#42](https://github.com/f6ra07nk14/structcast/issues/42) [#42](https://github.com/f6ra07nk14/structcast/issues/42) [#42](https://github.com/f6ra07nk14/structcast/issues/42)
* simplify type checks and improve validation logic in specifier module ([c8fcaa4](https://github.com/f6ra07nk14/structcast/commit/c8fcaa49eaaabefee242346e03569308ef89bc04))
* update build method signatures to accept optional PatternResult and improve validation handling ([2603f2a](https://github.com/f6ra07nk14/structcast/commit/2603f2a9a14c42001dc805acb466d7d8dc5b1d14))
* update instantiation patterns with improved validation and binding functionality ([952c1fc](https://github.com/f6ra07nk14/structcast/commit/952c1fcd855f4e4bd2a522630473ef3e4e16089a))
* use constant for alias in WithPipe model's pipe field ([a2e7e82](https://github.com/f6ra07nk14/structcast/commit/a2e7e82094e732a4c12440335bdd8eaff267508b))


### 🔨 Refactor

* consolidate import functions by delegating to utility functions and removing redundant code ([125899f](https://github.com/f6ra07nk14/structcast/commit/125899fbaccc86506fb9a95d85657175567b11b2))
* encapsulate instantiation logic in a helper function for improved readability and maintainability ([309fca7](https://github.com/f6ra07nk14/structcast/commit/309fca78dff9159f63b28e936f59c11370f426f1))
* enhance attribute validation by including module name in target ([d8f9e97](https://github.com/f6ra07nk14/structcast/commit/d8f9e9733ad0a7aeb1c1e4f5bd922202513b0be7))
* enhance convert_spec function with recursion control and timing ([041aa00](https://github.com/f6ra07nk14/structcast/commit/041aa000de7b15cfea097d4952b4c249d818b99c))
* enhance error handling in Jinja template processing and add recursion limits ([8a900f9](https://github.com/f6ra07nk14/structcast/commit/8a900f987b8713e0dd682d263a5a9b8ca0817679))
* enhance type handling in instantiation logic to support Sequence ([80c823d](https://github.com/f6ra07nk14/structcast/commit/80c823d866fc8dc0cf8cc9221f1975aa1f8acfe9))
* improve allowlist documentation and logic for module imports ([fd5106e](https://github.com/f6ra07nk14/structcast/commit/fd5106e78334f4725f3118c7772856089863cb8e))
* improve attribute access handling with detailed error messages ([4294492](https://github.com/f6ra07nk14/structcast/commit/42944920f6d7ae249279defccdcc63fde2688525))
* improve security error messages for blocked imports and attribute access ([5a33acb](https://github.com/f6ra07nk14/structcast/commit/5a33acb019269c7e221bfd3d98d9c7cc3b4d36de))
* move Jinja extensions to module-level variable and enhance configuration handling ([149012f](https://github.com/f6ra07nk14/structcast/commit/149012ffaa9a99d6c216e1250441e182e36084d5))
* move path validation functions to security module for better organization ([763e458](https://github.com/f6ra07nk14/structcast/commit/763e458090cc7b040619f94e13f8245ba5ae896e))
* move resolvers and accessers to module-level variables in SpecSettings ([634fc5a](https://github.com/f6ra07nk14/structcast/commit/634fc5a2373fcad5811653afea8d1c2d150f596d))
* optimize security settings assignment by replacing update calls with direct assignments ([2fa8299](https://github.com/f6ra07nk14/structcast/commit/2fa82994e6ee26453247ea4768287f9dec6daf5e))
* remove SPEC_CONSTANT and update resolver registration in specifier.py ([bfb3dea](https://github.com/f6ra07nk14/structcast/commit/bfb3deab23b29639a0a4bf87ce4fea755a552406))
* remove unused field patterns and conversion function from specifier.py ([dfb4f3e](https://github.com/f6ra07nk14/structcast/commit/dfb4f3e99699d18ece5843da8f9c75b2984ba383))
* rename and enhance attribute validation function for clarity and safety ([7606175](https://github.com/f6ra07nk14/structcast/commit/7606175a8ea093d9c1b270d9e75d65c76272a5be))
* rename global JinjaSettings variable for consistency ([45c0e9b](https://github.com/f6ra07nk14/structcast/commit/45c0e9b605a07a415e9e203ce695444f1eec4c1d))
* rename instantiation constants and introduce new exception classes ([e2ca2bd](https://github.com/f6ra07nk14/structcast/commit/e2ca2bd3443144991bf4fc96c693dc3f5abea59c))
* rename module from "instantiation" to "instantiator" ([4644630](https://github.com/f6ra07nk14/structcast/commit/4644630017e232724c27b04b8c04beb3458fb0e7))
* rename private variables for consistency and clarity ([a6993d5](https://github.com/f6ra07nk14/structcast/commit/a6993d5f7ab3964fb7fb8977b5c6d081471c7089))
* rename validate_access to validate_attribute and enhance validation logic ([333b6b6](https://github.com/f6ra07nk14/structcast/commit/333b6b69715bf373bb8e86a574267949008c6f94))
* reorganize imports in instantiator.py for clarity and structure ([331c7c7](https://github.com/f6ra07nk14/structcast/commit/331c7c7d61a1d0cac403a38b6828b77392db1b82))
* reorganize WithPipe class and remove unused code ([14bba9a](https://github.com/f6ra07nk14/structcast/commit/14bba9a058f6b81f548df8babdec8cd318d17e64))
* replace global settings instance with SECURITY_SETTINGS for improved clarity ([fc7e31c](https://github.com/f6ra07nk14/structcast/commit/fc7e31c9a3b7279a37611b15af1285f366afef63))
* simplify casting function by introducing _casting utility ([28a435d](https://github.com/f6ra07nk14/structcast/commit/28a435d060104ff4cae6fdbd137be717c8dd7eec))
* simplify dataclass utility by removing overloads and using dataclass_transform ([c297c79](https://github.com/f6ra07nk14/structcast/commit/c297c79ba1dca6bf237d2bfb6ad286fea761e781))
* simplify DEFAULT_DANGEROUS_DUNDERS initialization and update allowed modules for structcast ([e9846fb](https://github.com/f6ra07nk14/structcast/commit/e9846fb669943f84e741c5569fa2d86adc3e79a6))
* simplify JinjaTemplate by removing unnecessary inheritance and model configuration ([d22f9ca](https://github.com/f6ra07nk14/structcast/commit/d22f9caddb7268d1b9b78865e11a667c48e836f1))
* simplify security settings by removing private attributes and using a global instance ([2a552bd](https://github.com/f6ra07nk14/structcast/commit/2a552bdca8437144ab75a9e36b8b00d2fb089251))
* simplify structured specification conversion logic for improved readability ([fd69c8b](https://github.com/f6ra07nk14/structcast/commit/fd69c8b21bbc7b4673531bee7caa447eaba9de65))
* simplify test_security.py by removing unused imports and consolidating context manager usage ([206c00f](https://github.com/f6ra07nk14/structcast/commit/206c00fb58ac5a9116cf4433353527ababb12bec))
* streamline _access_default function by simplifying indexing logic and improving error handling ([95f46e5](https://github.com/f6ra07nk14/structcast/commit/95f46e597fbae249dd1ec40fa61191c5ff86c931))
* streamline construct function and encapsulate logic in _construct method ([5214e7a](https://github.com/f6ra07nk14/structcast/commit/5214e7af83787c8c21391c9e46288e0e1b875154))
* streamline security settings management by consolidating checks and removing unused constants ([9691c98](https://github.com/f6ra07nk14/structcast/commit/9691c98103380e45bc69eb6ab32ea5024304ed0d))
* streamline security timeout check for clarity ([9dc8076](https://github.com/f6ra07nk14/structcast/commit/9dc80760b6fb0a291e66618a87febb73065310da))
* update allowed modules structure and enhance security configuration ([7ddd460](https://github.com/f6ra07nk14/structcast/commit/7ddd4600708e2c643e5b21d926e4331b930fcbc5))
* update CallPattern and BindPattern to support flexible call and bind argument types ([ad04bf7](https://github.com/f6ra07nk14/structcast/commit/ad04bf7a7fba31ba7e508624d00cf8c6de7c4f78))
* update import statements for clarity and consistency ([e4fafc2](https://github.com/f6ra07nk14/structcast/commit/e4fafc26774542701977151dc3c4b82a2042b263))
* update parameter types in function signatures for clarity and consistency ([486593a](https://github.com/f6ra07nk14/structcast/commit/486593a27dfbdeecfe6cc633a456f92080535ea2))
* update PathLike type alias to use imported PathLike for consistency ([8e73123](https://github.com/f6ra07nk14/structcast/commit/8e73123ca7d6d4b1f6289d6cbd5104674a797f7a))


### ✨ Style

* clean up imports and improve type casting in utility functions ([5d8d5ab](https://github.com/f6ra07nk14/structcast/commit/5d8d5ab8db25c5eb2e2b8f2c8c58b533a5817c24))
* clean up whitespace in CI configuration for consistency ([a4d4bef](https://github.com/f6ra07nk14/structcast/commit/a4d4bef07e1afc902b78d7d7746d7271ce1891d0))
* format CI configuration for consistency and readability ([7e6296b](https://github.com/f6ra07nk14/structcast/commit/7e6296bda01f35e89cf4596864069ea55755d38f))
* increase max-branches limit in pylint configuration for improved analysis ([4e743aa](https://github.com/f6ra07nk14/structcast/commit/4e743aa737ac44dfc513f894021752b9e28dd200))
* update allowed_modules parameter type to improve security context configuration ([d1cf733](https://github.com/f6ra07nk14/structcast/commit/d1cf73358079373a64b10be1d835be870feda93b))
* update allowed_modules type hint to support optional strings ([bc06691](https://github.com/f6ra07nk14/structcast/commit/bc06691f7a3cb4f0e75e9db672fc21cc3e437957))
* update type hints in security module to use tuple with ellipsis for improved type safety ([3763137](https://github.com/f6ra07nk14/structcast/commit/3763137e4c00a9ca76f9ba5650d1a89c041373b8))


### 🚨 Tests

* add comprehensive tests for construct function in specifier module ([162fd86](https://github.com/f6ra07nk14/structcast/commit/162fd86115b1ad00ff19b5d69868e7e8b333b396))
* add comprehensive tests for instantiation functionalities and security features ([c1e4384](https://github.com/f6ra07nk14/structcast/commit/c1e43842c24028fc3861c650944456d4343f2f24))
* add comprehensive tests for instantiation functionalities, including pattern validation and security checks ([e6450c7](https://github.com/f6ra07nk14/structcast/commit/e6450c7657eabf34bab4e42020722931c6971936))
* add comprehensive tests for RawSpec and ObjectSpec classes ([1a5b100](https://github.com/f6ra07nk14/structcast/commit/1a5b100a478f0383fbc4514760321a5d63aa198d))
* add comprehensive unit tests for Jinja template functionality ([85346ab](https://github.com/f6ra07nk14/structcast/commit/85346ab20f80a15588f362089b2cd89565cf7fdf))
* add context manager for temporary security configuration in tests ([e03e8b6](https://github.com/f6ra07nk14/structcast/commit/e03e8b6c784df9a99246b7436e4945adff40d021))
* add initial test files for core functionalities and instantiation ([5277372](https://github.com/f6ra07nk14/structcast/commit/52773722692be7d86369ab2168af9857c2978a69))
* add security tests for file loading and path resolution ([c9f434f](https://github.com/f6ra07nk14/structcast/commit/c9f434fd5678412cff2d88ed74814a1fb9e89d4e))
* add tests for base utility functions including YAML loading and dumping ([01769a6](https://github.com/f6ra07nk14/structcast/commit/01769a606112d3966938c2628f47dcfaffbaed2b))
* add tests for convert_spec and construct functions, including custom mappings and error handling ([87db8d4](https://github.com/f6ra07nk14/structcast/commit/87db8d4ab2b66661ee5b48c76be8c1dfde87f3e9))
* add tests for recursion depth protection and improve attribute validation ([345acfa](https://github.com/f6ra07nk14/structcast/commit/345acfac720f8da7d73e86486dd64f2f6847a8b7))
* add tests for YAML constructor and security configuration functionalities ([f75a35c](https://github.com/f6ra07nk14/structcast/commit/f75a35c0e48a3bed254cba0b75744bd88e4e9169))
* add unit tests for specifier module functionality ([26a7133](https://github.com/f6ra07nk14/structcast/commit/26a71335316661a4dfe669316b3b6a0fc94c09d9))
* add unit tests for StructCast utilities including path registration and YAML loading ([8a01829](https://github.com/f6ra07nk14/structcast/commit/8a01829c8c0abddbbb335641c2f950d6bb41ebc3))
* implement timeout protection and enhance error message sanitization in instantiation tests ([03cf77c](https://github.com/f6ra07nk14/structcast/commit/03cf77c592e0b69122ecfc49ae807ecb05c249ac))
* update return type annotation for Jinja context manager to Generator ([887c578](https://github.com/f6ra07nk14/structcast/commit/887c578a9ef83b32d22c1458aa9317fbe0db6936))
* update security error message matches for blocked imports and builtins ([b60fb85](https://github.com/f6ra07nk14/structcast/commit/b60fb859b1b910038940129cd97e9e60e2123040))
* use unique filenames for temporary YAML files in tests ([da23563](https://github.com/f6ra07nk14/structcast/commit/da23563f582fe8903ba0bf1e0636d6a3b6e8ec02))
