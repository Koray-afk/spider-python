/*$Id$*/

/* global WebMessanger*/
(function (window) {
    var document = window.document;
    var zgssearch = (function (zgssearch) {
        zgssearch = window.zgssearch || {};

        /*Browser detect - starts*/
        zgssearch.userAgent = window.navigator.userAgent;
        zgssearch.isIE = (zgssearch.userAgent.indexOf("MSIE") !== -1 || zgssearch.userAgent.indexOf("Trident") !== -1);
        zgssearch.isLinux = (zgssearch.userAgent.indexOf("Linux") !== -1 || zgssearch.userAgent.indexOf("Linux") !== -1);
        zgssearch.isWindows = (zgssearch.userAgent.indexOf("Win") !== -1 || zgssearch.userAgent.indexOf("Win") !== -1);

        zgssearch.detectBrowser = function () {
            if ((zgssearch.userAgent.indexOf("Opera") || zgssearch.userAgent.indexOf('OPR')) != -1) {
                return 'Opera';  //NO I18N
            }
            else if (zgssearch.userAgent.indexOf("Edg") != -1) {
                return 'Edge';  //NO I18N
            }
            else if (zgssearch.userAgent.indexOf("Chrome") != -1) {
                return 'Chrome';  //NO I18N
            }
            else if (zgssearch.userAgent.indexOf("Safari") != -1) {
                return 'Safari';  //NO I18N
            }
            else if (zgssearch.userAgent.indexOf("Firefox") != -1) {
                return 'Firefox';  //NO I18N
            }
            else if ((zgssearch.userAgent.indexOf("MSIE") != -1) || (!!document.documentMode == true)) {
                return 'IE';  //NO I18N
            }
            else {
                return 'Unknown';  //NO I18N
            }
        };

        zgssearch.detectBrowserVersion = function() {
            var ua = zgssearch.userAgent, tem,
                M = ua.match(/(opera|chrome|safari|firefox|msie|trident(?=\/))\/?\s*(\d+)/i) || [];
            if(/trident/i.test(M[1])){
                tem = /\brv[ :]+(\d+)/g.exec(ua) || [];
                return {name:'IE',version:(tem[1] || '')};  //NO I18N
            }
            if(M[1]=== 'Chrome'){
                tem = ua.match(/\b(OPR|Edge)\/(\d+)/);
                if(tem != null) return {name:tem[1].replace('OPR', 'Opera'),version:tem[2]};
            }
            M = M[2]? [M[1], M[2]]: [navigator.appName, navigator.appVersion, '-?'];
            if((tem = ua.match(/version\/(\d+)/i))!= null)
                M.splice(1, 1, tem[1]);
            return {name:M[0], version:M[1]};
        };
        /*Browser detect - ends*/

        zgssearch.ZSNetwork = {

            imageRenderer : {

                renderImage : function(url,imgElem, callback){
                    if(imgElem){
                        zgssearch.renderPhoto("", url, imgElem.class_name, imgElem.errorClass, imgElem.img_elem);
                    }else{
                        callback(url)
                    }
                },
                renderUserImage : function(imgObj,callback){
                    if(imgObj.imgEle){
                        zgssearch.renderUserPhoto(imgObj);
                    }else{
                        callback? callback(imgObj.url) : "";
                    }
                }

            },

            getSearchResultsForSSE: function (searchURL) {
                zgssearch.eventSource = new EventSource(searchURL),
                    zgssearch.pendingDecryptions = []; // clear
                    zgssearch.eventSource.addEventListener("Waf-Encryption-Key", function (event) {
                        zgssearch.handleSearchResults("Waf-Encryption-Key", event.data); //NO I18N
                    }),
                    zgssearch.eventSource.addEventListener("initial_Weightage", function (event) {
                        zgssearch.handleSearchResults("IWEIGHT", event.data); //NO I18N
                    }),
                    zgssearch.eventSource.addEventListener("version", function (event) {
                        zgssearch.handleSearchResults("VERSION", event.data);  //NO I18N
                    }),
                    zgssearch.eventSource.addEventListener("result", function (event) {
                        zgssearch.handleSearchResults("RESULT", event.data);  //NO I18N
                    }),
                    zgssearch.eventSource.addEventListener("nlp_tracer", function (event) {
                        zgssearch?.gsnlptracer?.setAndShowNLPTracerData(event.data);
                    }),
                    zgssearch.eventSource.addEventListener("weightage", function (event) {
                        zgssearch.handleSearchResults("WEIGHT", event.data);  //NO I18N
                    }),
                    zgssearch.eventSource.onmessage = function (event) {
                        zgssearch.network.removeEventSource();
                        zgssearch.handleSearchResults("CLOSE", event);  //NO I18N
                    },
                    zgssearch.eventSource.onerror = function (event) {
                        zgssearch.network.removeEventSource();
                        zgssearch.handleSearchResults("ERROR", event); //NO I18N
                    }
            },

            abortOngoingCalls: function () {
                zgssearch.abortXMLHTTPReq(zgssearch.xmlhttpReq);
                zgssearch.network.removeEventSource();
            },

            abortOngoingCalloutCalls: function () {
                zgssearch.abortXMLHTTPReq(zgssearch.xmlhttpCalloutReq);
                zgssearch.network.removeEventSource();
            },

            abortOngoingAdvSearchCalls: function () {
                zgssearch.abortXMLHTTPReq(zgssearch.advSearchXMLHttpReq);
                zgssearch.network.removeEventSource();
            },

            removeEventSource: function () {
                if (zgssearch.eventSource !== undefined) {
                    zgssearch.eventSource.close();
                    zgssearch.eventSource = undefined;
                }
            },

            xmlHttpReq: function (method, url, abort, callback) {
                if (abort) {
                    zgssearch.abortXMLHTTPReq(zgssearch.xmlhttpReq);
                }
                zgssearch.xmlhttpReq = zgssearch.getRequestObject();
                zgssearch.xmlhttpReq.onreadystatechange = function (event) {
                    if (zgssearch.xmlhttpReq.readyState === 4) {
                        if (zgssearch.xmlhttpReq.status === 200) {
                            callback({
                                response: zgssearch.xmlhttpReq.responseText,
                                status: "success", //NO I18N
                                result: zgssearch.xmlhttpReq,
                                args: zgssearch.xmlhttpReq.args
                            });
                        }
                        else {
                            callback({
                                response: event,
                                status: "error", //NO I18N
                                result: zgssearch.xmlhttpReq,
                                args: zgssearch.xmlhttpReq.args
                            });
                        }

                    }
                };
                zgssearch.xmlhttpReq.open(method, url, true);
                zgssearch.xmlhttpReq.send();
            },

            handleAjaxRequest: function (url_obj) {
                let req = window._jQueryGS.ajax(url_obj);
                let args = url_obj.args || {};
                if (args && !_jQueryGS.isEmptyObject(args) && args.hasOwnProperty("isCalloutReq") && args.isCalloutReq)
                {
                    zgssearch.xmlhttpCalloutReq = req;
                }
            },

            handleUrlPayloadEncryption: function (url_obj) {
                if(zgssearch.GSConstant.isPayloadEncryptionEnabled && url_obj.data && zgssearch.ZWAF)
                {
                    zgssearch.ZWAF.Encryption.encrypt(url_obj.data).then(encryptedResponse => {
                        url_obj.data = encryptedResponse.data;
                        url_obj.headers = {
                            "Waf-Encryption-Key": encryptedResponse.key,  //NO I18N
                            "Waf-Encryption-Id": zgssearch.ZWAF.Encryption.getWafEncryptionId()  //NO I18N
                        }
                        url_obj.dataType = "text"; //NO I18N
                        ZSNetwork.handleAjaxRequest(url_obj);
                    });
                }
                else
                {
                    ZSNetwork.handleAjaxRequest(url_obj);
                }
            },

            handleUrlResponseDecryption: function (data, status, xhr, callback) {
                let wafEncryptionKeyHeader = zgssearch?.ZWAF?.Encryption?.constants?.WAF_ENCRYPTION_KEY_HEADER;
                let wafEncryptionKey = wafEncryptionKeyHeader ? xhr.getResponseHeader(wafEncryptionKeyHeader) : ""; //NO I18N
                if(zgssearch.GSConstant.isPayloadEncryptionEnabled && data && wafEncryptionKey)
                {
                    zgssearch.ZWAF.Encryption.decrypt(data, wafEncryptionKey).then(decryptedResponse => {
                        callback(decryptedResponse, status, xhr);
                    });
                }
                else
                {
                    callback(data, status, xhr);
                }
            },

            uri: function (url_obj) {
                url_obj.successCallback = url_obj.success;
                url_obj.success = function (result, status, xhr) {
                    xhr ? xhr.args = this.args : xhr = result;
                    xhr.args = this.args;
                    zgssearch.network.handleUrlResponseDecryption(result, status, xhr, url_obj.successCallback);
                }
                if ("POST" === url_obj.type || "DELETE" === url_obj.type || "PUT" === url_obj.type) {
                    return zgssearch.network.getCookie("CSRF_TOKEN", function (csrfParam) {//NO I18N
                        url_obj.data = "undefined" != typeof url_obj.data ? url_obj.data += "&" + GSConstant.csrfName + "=" + csrfParam : csrfParam;//NO I18N
                        ZSNetwork.handleUrlPayloadEncryption(url_obj);
                    });
                }
                else
                {
                    ZSNetwork.handleUrlPayloadEncryption(url_obj);
                }
            },

            upload_file: function (url_obj) {
                if(url_obj.method === "POST")
                {
                    zgssearch.network.getCookie("CSRF_TOKEN", function (csrfValue){     //NO I18N
                        var formData = url_obj.data;
                        if(csrfValue)
                        {
                            formData.append(GSConstant.csrfName, csrfValue);
                        }
                    });
                }
                window._jQueryGS.ajax(url_obj);
            },

            download_file : function (url) {
                var iframe = document.createElement('iframe');//No I18N
                iframe.frameBorder = 0;
                iframe.id = "download_iframe";//No I18N
                iframe.src = url;
                iframe.style = "display:none";//No I18N
                var parent = (zgssearch.isPreviewOpenedInComponent) ? "zgs20_pcSearch" : "zgs20_globalsearch";//NO I18N
                document.getElementById(parent).appendChild(iframe);
                setTimeout(function () {
                    iframe.parentElement.removeChild(iframe);
                }, 50000);
            },

            getFingerPrintFilePath: function (filepath, folderPath) {
                //https://<static_domain_url>/zohosearch/<build_date>/js/filename.<fingerprint_value>.js
                var pathName = (folderPath === "embeddashboards") ? folderPath : zgssearch.GSConstant.BUILD_DATE;  //NO I18N
                var filePrefix = window.location.protocol + "//" + zgssearch.GSConstant.STATIC_RESOURCE_SERVER + "/" + zgssearch.gscomponent.gsserver + "/" + pathName + "/"; //NO I18N
                if ((zgssearch.gscomponent.hasOwnProperty("isFingerprintEnabled") && zgssearch.gscomponent.isFingerprintEnabled) && zgssearch.gscomponent.hasOwnProperty(filepath)) {
                    if (folderPath === "embeddashboards") {
                        return zgssearch.gsbuildDetails[filepath];
                    }
                    return filePrefix + zgssearch.gsbuildDetails[filepath];
                }
                return filePrefix + filepath;
            },

            setIntegrityValue: function (domEle, checksumValue) {
                domEle.setAttribute("integrity", checksumValue);
                domEle.setAttribute("crossorigin","anonymous");
            },

            loadSRICSSFile: function (fileName, callback, folderPath) {//this will load file with fingerprinted & SRI value
                if (fileName && typeof fileName !== undefined) {
                    var fileURL = "", component_checksums = "";
                    if((fileName.indexOf("wmsbar") > -1)) {
                        fileURL = fileName;
                        component_checksums = (wms_css_url_integrity ? wms_css_url_integrity : "");
                    } else {
                        fileURL = zgssearch.network.getFingerPrintFilePath(fileName, folderPath);
                    }
                    var checksumValue = (zgssearch.gsbuildDetails.hasOwnProperty("checksums") && zgssearch.gsbuildDetails.checksums.hasOwnProperty(fileName)) ? zgssearch.gsbuildDetails.checksums[fileName] : component_checksums;
                    var domCSS = document.createElement("link");
                    domCSS.setAttribute("rel", "stylesheet");
                    domCSS.setAttribute("type", "text/css");
                    if(checksumValue) {
                        zgssearch.network.setIntegrityValue(domCSS, checksumValue);
                    }
                    domCSS.setAttribute("href", fileURL);
                    domCSS.onload = function () {
                        if (!zgssearch.cssLoaded) {
                            zgssearch.cssLoaded = true;
                        }
                        callback ? callback() : "";
                    };
                    document.getElementsByTagName("head").item(0).appendChild(domCSS);
                }
            },

            loadJSFile: function(fileURL, callback) {
               if (typeof fileURL !== undefined) {
                   var scriptEle = document.createElement('script');
                   scriptEle.setAttribute("type", "text/javascript"); //NO I18N
                   scriptEle.setAttribute("src", fileURL);
                   scriptEle.onload = function() {
                       callback ? callback() : "";
                   };
                   document.getElementsByTagName("head").item(0).appendChild(scriptEle);
               }
            },

            loadSRIJSFile: function (fileName, callback, folderPath) {//this will load file with fingerprinted & SRI value
                if (fileName && typeof fileName !== undefined) {
                    var fileURL = "", component_checksums = "";
                    if(fileName.indexOf("wmsbar") > -1) {
                        fileURL = fileName;
                        component_checksums = (wms_js_url_integrity ? wms_js_url_integrity : "");
                    } else {
                        fileURL = zgssearch.network.getFingerPrintFilePath(fileName, folderPath);
                    }
                    //For workdrive, it is temporary solution, till they provide the zip via ant
                    component_checksums = (fileName.indexOf("workdrive-components") > -1) ? zgssearch.workdrive_component_integrity : component_checksums;
                    var checksumValue = (zgssearch.gsbuildDetails.hasOwnProperty("checksums") && zgssearch.gsbuildDetails.checksums.hasOwnProperty(fileName)) ? zgssearch.gsbuildDetails.checksums[fileName] : component_checksums;
                    var scriptEle = document.createElement('script');
                    scriptEle.setAttribute("type", "text/javascript");  //NO I18N
                    if(checksumValue) {
                        zgssearch.network.setIntegrityValue(scriptEle, checksumValue);
                    }
                    scriptEle.setAttribute("src", fileURL);
                    scriptEle.onload = function () {
                        callback ? callback() : "";
                    };
                    document.getElementsByTagName("head").item(0).appendChild(scriptEle);
                }
            },

            loadSRIJSFileForFingerprintedURL: function (fileName, callback) {//this will load file with fingerprinted & SRI value
                if (fileName && typeof fileName !== undefined) {
                    var checksumValue = (zgssearch.gsbuildDetails.hasOwnProperty("checksums") && zgssearch.gsbuildDetails.checksums.hasOwnProperty(fileName)) ? zgssearch.gsbuildDetails.checksums[fileName] : ""; //NO I18N
                    var scriptEle = document.createElement('script');
                    scriptEle.setAttribute("type", "text/javascript");  //NO I18N
                    if(checksumValue && checksumValue != "") {
                        zgssearch.network.setIntegrityValue(scriptEle, checksumValue);
                    }

                    var fileURL = zgssearch.gsbuildDetails.hasOwnProperty(fileName) && zgssearch.gsbuildDetails[fileName];
                    fileURL = window.location.protocol + "//" + zgssearch.GSConstant.STATIC_RESOURCE_SERVER + fileURL;
                    scriptEle.setAttribute("src", fileURL);
                    scriptEle.onload = function () {
                        callback ? callback() : "";
                    };
                    document.getElementsByTagName("head").item(0).appendChild(scriptEle);
                }
            },

            loadCSSFile: function (fileURL, callback) {
                if (fileURL && typeof fileURL !== undefined) {
                    var domCSS = document.createElement("link");
                    domCSS.setAttribute("rel", "stylesheet");
                    domCSS.setAttribute("type", "text/css");
                    domCSS.setAttribute("href", fileURL);
                    domCSS.onload = function () {
                        if (!zgssearch.cssLoaded) {
                            zgssearch.cssLoaded = true;
                        }
                        callback ? callback() : "";
                    };
                    document.getElementsByTagName("head").item(0).appendChild(domCSS);
                }
            },

            loadJSFile: function (fileURL, callback) {
                if (typeof fileURL !== undefined) {
                    var scriptEle = document.createElement('script');
                    scriptEle.setAttribute("type", "text/javascript");  //NO I18N
                    scriptEle.setAttribute("src", fileURL);
                    scriptEle.onload = function () {
                        callback ? callback() : "";
                    };
                    document.getElementsByTagName("head").item(0).appendChild(scriptEle);
                }
            },

            getCookie: function (cname, callback) {
                var name = cname + "=";
                var ca = document.cookie.split(';');
                for (var i = 0; i < ca.length; i++) {
                    var c = ca[i].trim();
                    if (c.indexOf(name) === 0) {
                        return callback(c.substring(name.length, c.length));
                    }
                }
            }

        };
        zgssearch.network = zgssearch.ZSNetwork;

        zgssearch.gscomponent = zgssearch.gscomponent || {};
        zgssearch.GSConstant = zgssearch.GSConstant || {LVS_ENTRY:"zgssearch"};   //NO I18N
        zgssearch.GSConstant.supportedZSLanguages = zgssearch.GSConstant.supportedZSLanguages || ["en", "zh", "baihui_en", "baihui_zh", "sd_IN" ,"fa_IR", "et_EE", "gu_IN", "ur_PK", "ko_KR", "km_KH", "ta_IN", "as_IN", "hi_IN", "el_GR", "fil-PH", "tr_TR", "sl_SI", "ja_JP", "az_Latn-AZ", "it_IT", "es_ES", "pa_IN", "lo_LA", "bg_BG", "da_DK", "ms_MY", "cs_CZ", "nb_NO", "bn_IN", "de_DE", "lt_LT", "nl_NL", "ca_ES", "mr_IN", "zh_CN", "sq_AL", "si_LK", "my_MM", "th_TH", "uk_UA", "he_IL", "sv_SE", "sr_Latn-RS", "hr_HR", "fi_FI", "pt_PT", "hu_HU", "eu_ES", "ro_RO", "lv_LV", "pt_BR", "ne_NP", "ar_EG", "mk_MK", "vi_VN", "kn_IN", "fr_FR", "jv", "te_IN", "ru_RU", "pl_PL", "ks_IN", "mai_IN", "ml_IN" ,"or_IN", "sat_IN", "brx_IN", "doi_IN", "kok_IN", "sd_IN", "mni_IN", "sa_IN"]; //NO I18N
        zgssearch.GSConstant.rtlSupportedZSLanguages = zgssearch.GSConstant.rtlSupportedZSLanguages || ["ar_EG","ur_PK","fa_IR","he_IL","ks_IN"];  //NO I18N
        zgssearch.getbd = "/"+zgssearch.GSConstant.LVS_ENTRY+"/getbd";  //NO I18N
        zgssearch.isExtension = false;
        zgssearch.thirdPartyCookieDisabled = false;

        zgssearch.getGSConstantObj = function () {
            return zgssearch?.GSConstant;
        };

        zgssearch.GSConstant.languageVsCountryObj = {
            "ar": ["ar_EG"], //NO I18N
            "as": ["as_IN"], //NO I18N
            "az": ["az_Latn-AZ"], //NO I18N
            "bg": ["bg_BG"], //NO I18N
            "bn": ["bn_IN"], //NO I18N
            "cs": ["cs_CZ"], //NO I18N
            "da": ["da_DK"], //NO I18N
            "de": ["de_DE"], //NO I18N
            "el": ["el_GR"], //NO I18N
            "es": ["es_ES"], //NO I18N
            "fi": ["fi_FI"], //NO I18N
            "fr": ["fr_FR"], //NO I18N
            "gu": ["gu_IN"], //NO I18N
            "hi": ["hi_IN"], //NO I18N
            "hr": ["hr_HR"], //NO I18N
            "hu": ["hu_HU"], //NO I18N
            "it": ["it_IT"], //NO I18N
            "ja": ["ja_JP"], //NO I18N
            "kn": ["kn_IN"], //NO I18N
            "ko": ["ko_KR"], //NO I18N
            "lt": ["lt_LT"], //NO I18N
            "mr": ["mr_IN"], //NO I18N
            "ms": ["ms_MY"], //NO I18N
            "nb": ["nb_NO"], //NO I18N
            "ne": ["ne_NP"], //NO I18N
            "nl": ["nl_NL"], //NO I18N
            "pa": ["pa_IN"], //NO I18N
            "pl": ["pl_PL"], //NO I18N
            "pt": ["pt_PT", "pt_BR"], //NO I18N
            "ro": ["ro_RO"], //NO I18N
            "ru": ["ru_RU"], //NO I18N
            "sl": ["sl_SI"], //NO I18N
            "sr": ["sr_Latn-RS"], //NO I18N
            "sv": ["sv_SE"], //NO I18N
            "ta": ["ta_IN"], //NO I18N
            "te": ["te_IN"], //NO I18N
            "th": ["th_TH"], //NO I18N
            "tr": ["tr_TR"], //NO I18N
            "uk": ["uk_UA"], //NO I18N
            "ur": ["ur_PK"], //NO I18N
            "vi": ["vi_VN"], //NO I18N
            "zh": ["zh_CN"], //NO I18N
            "ca": ["ca_ES"], //NO I18N
            "et": ["et_EE"], //NO I18N
            "eu": ["eu_ES"], //NO I18N
            "fa": ["fa_IR"], //NO I18N
            "he": ["he_IL"], //NO I18N
            "jv": ["jv"], //NO I18N
            "km": ["km_KH"], //NO I18N
            "lo": ["lo_LA"], //NO I18N
            "lv": ["lv_LV"], //NO I18N
            "mk": ["mk_MK"], //NO I18N
            "ph": ["fil-PH"], //NO I18N
            "si": ["si_LK"], //NO I18N
            "sq": ["sq_AL"], //NO I18N
            "my": ["my_MM"], //NO I18N
            "in": ["id_ID"], //NO I18N
            "ks": ["ks_IN"], //NO I18N
            "mai": ["mai_IN"], //NO I18N
            "ml": ["ml_IN"], //NO I18N
            "or": ["or_IN"], //NO I18N
            "sat": ["sat_IN"], //NO I18N
            "brx": ["brx_IN"],  //NO I18N
            "doi": ["doi_IN"],  //NO I18N
            "kok": ["kok_IN"],  //NO I18N
            "sd": ["sd_IN"],  //NO I18N
            "mni": ["mni_IN"],  //NO I18N
            "sa": ["sa_IN"]  //NO I18N
        };

        /*Client Error Handling*/
        zgssearch.console = window.console;
        var zsConsole = zgssearch.console;
        zgssearch.throwClientError = function (errMsg, exception) {
            errMsg = exception ? errMsg +  " " + exception : errMsg;
            zsConsole.log("ZS: " + errMsg); //NO I18N
            if(typeof murphy !== "undefined") {
                murphy.error(exception);
            }
        };
        zgssearch.logTrace = function (ex) {
            zsConsole.log(ex);
        };
        /*IE prototype override*/
        zgssearch.includes = function (target, array) {
            if (!String.prototype.includes) {//To check browser supports or not
                return array.indexOf(target) !== -1;
            }
            return array.includes(target);
        };
        zgssearch.assignObject = function (target, initObj) {
            if (typeof Object.assign != 'function') {
                Object.assign = function (target) {
                    'use strict';//NO I18N
                    if (target == null) {
                        zgssearch.throwClientError('Cannot convert undefined or null to object');//NO I18N
                    }
                    target = Object(target);
                    for (var index = 1; index < arguments.length; index++) {
                        var source = arguments[index];
                        if (source != null) {
                            for (var key in source) {
                                if (Object.prototype.hasOwnProperty.call(source, key)) {
                                    target[key] = source[key];
                                }
                            }
                        }
                    }
                    return target;
                };
            }
            return  Object.assign(target, initObj);
        };

        zgssearch.initLoadZSFiles = function (initObj) {
            zgssearch.gsbuildDetails = zgssearch.jsonParse(initObj);
            zgssearch.loadZSFiles();
        };

        zgssearch.initZGSHandler = function (initObj) {
            var isZSLiteOrigin = window.hasOwnProperty("ZSLite") ? window.ZSLite : false;  //NO I18N
            if(!isZSLiteOrigin) {
                initObj = initObj || {};
                if(initObj){
                    if(initObj.thirdPartyCookieDisabled != undefined){
                        zgssearch.thirdPartyCookieDisabled = initObj.thirdPartyCookieDisabled;
                    }
                    if(initObj.network){
                        zgssearch.network = initObj.network;
                    }
                    if(initObj.source && initObj.source === "extension"){
                        zgssearch.isExtension = true;
                    }
                }

                initObj = zgssearch.assignObject(initObj, zgssearch.gsbuildDetails);
                initObj.gsrebrand = initObj.hasOwnProperty("gsrebrand") ? initObj.gsrebrand : ((typeof (WebMessanger) != "undefined") ? (WebMessanger.rebrand || "") : "");  //NO I18N
                initObj.gslanguage = initObj.hasOwnProperty("gslanguage") ? initObj.gslanguage : ((typeof (WebMessanger) != "undefined") ? (WebMessanger.language || "") : "");  //NO I18N
                initObj.gscountry = initObj.hasOwnProperty("gscountry") ? initObj.gscountry : ((typeof (WebMessanger) != "undefined") ? (WebMessanger.countrycode || "") : "");  //NO I18N

                zgssearch.gscomponent = zgssearch.assignObject(zgssearch.gscomponent, initObj);
                if (!initObj.hasOwnProperty("getbdDataObtained") && !initObj.hasOwnProperty("isFingerprintEnabled")) {
                    zgssearch.getBuildDetails();
                }
                else {
                    zgssearch.initLoadZSFiles(initObj);
                }
            } else {

                if (window.ZSLite && (window.hasOwnProperty("openZiaAPIHandler") || window.hasOwnProperty("openZSHandler"))) {//In parent window.ZSLite will be false, in child window.ZSLite set as true via services library
                    var suiteScopeName = window.hasOwnProperty("openZiaAPIHandler") ? "openZiaAPIHandler" : "openZSHandler";  //NO I18N
                    zgssearch.serviceSearch = function (service, query, filterObj) {
                        window.hasOwnProperty("openZiaAPIHandler") ? window[suiteScopeName]("zgssearch.serviceSearch",[service, query, filterObj]) : window[suiteScopeName]([service, query, filterObj]);
                    };

                    // Teams can use this function who are going to call with only for serviceSearch
                    zgssearch.helpSearch = function (query, appToSearch, categType) {
                        window.hasOwnProperty("openZiaAPIHandler") ? window[suiteScopeName]("zgssearch.helpSearch",[query, appToSearch, categType]) : window[suiteScopeName]([query, appToSearch, categType]);
                    };

                    // Teams can use this function who are going to call with only for open
                    zgssearch.open = function () {
                        window.hasOwnProperty("openZiaAPIHandler") ? window[suiteScopeName]("zgssearch.open") : window[suiteScopeName]();
                    };

                    // Teams can use this function who are going to call with only plain query
                    zgssearch.search = function (query) {
                        window.hasOwnProperty("openZiaAPIHandler") ? window[suiteScopeName]("zgssearch.search",[query]) : window[suiteScopeName]([query]);
                    };

                    // Teams can use this function who are going to call with query, type, advanced search fields, etc, ...
                    zgssearch.advancedSearch = function (paramObj) {
                        window.hasOwnProperty("openZiaAPIHandler") ? window[suiteScopeName]("zgssearch.advancedSearch",[paramObj]) : window[suiteScopeName]([paramObj]);
                    };
                }
            }
        };

        zgssearch.jsonParse = function (data) {
            try {
                if (typeof data === 'string') {
                    return JSON.parse(data);
                }
            } catch (ex) {
                zgssearch.throwClientError("Error while parsing json data", ex); //NO I18N
            }
            return data;
        };

        zgssearch.abortXMLHTTPReq = function (httpReq) {
            if (httpReq) {
                httpReq.abort();
            }
            return;
        };

        zgssearch.getRequestObject = function () {
            try {
                return new XMLHttpRequest();
            } catch (ex) {
                zgssearch.throwClientError("Unable to create XML Http Object for Ajax Request.", ex); //NO I18N
                throw ex;
            }
        };

        zgssearch.getBuildDetails = function () {
            zgssearch.network.xmlHttpReq("GET", zgssearch.getbd, true, function (result) {//No I18N
                if (result && result.status && result.status != "error") {
                    zgssearch.initLoadZSFiles(result.response);
                    zgssearch.bdLoaded = true;
                }
            });
        };

        zgssearch.setGSConstantObj = function (jsonObj) {
            for (var propt in jsonObj) {
                zgssearch.GSConstant[propt] = jsonObj[propt];
            }
        };

        zgssearch.checkAndloadFontAndJqueryFile = function(){
            var userLanguage = zgssearch.getCurrentLanguage();
            var nicLanguageFont =( userLanguage === "mni_IN") ? "manipurifont" : "santhalifont";  //NO I18N
            var nicLanguageFontFile = "css/"+nicLanguageFont+".css";  //NO I18N
            if((userLanguage === "mni_IN" && (zgssearch.isLinux || zgssearch.isWindows)) || (userLanguage === "sat_IN" && (zgssearch.isLinux))) {
                zgssearch.network.loadSRICSSFile(nicLanguageFontFile, zgssearch.loadJQueryFile);
            }
            else {
                zgssearch.loadJQueryFile();
            }
        };

        zgssearch.loadGSFile = function () {
            if (!zgssearch.cssLoaded) {
                zgssearch.network.loadSRICSSFile(zgssearch.GSConstant.resultNewCSSURL, zgssearch.checkAndloadFontAndJqueryFile);
            }
            else {
                zgssearch.checkAndloadFontAndJqueryFile();
            }
        };

        zgssearch.loadJQueryFile = function () {
            var ZSJqueryCoreExists = window.hasOwnProperty("ZSJqueryCoreObj") ? (window.ZSJqueryCoreObj.version === "3.6.0") : false;  //NO I18N
            if ((typeof (jQuery) !== "undefined" && typeof (jQuery) !== undefined && jQuery().jquery === "3.6.0") || ZSJqueryCoreExists) { //already jquery availabe in parent DOM
                if (ZSJqueryCoreExists) {
                    window._jQueryGS = window.ZSJqueryCoreObj.scope;
                }
                else {
                    window._jQueryGS = jQuery;
                }
                window.jQuery = (typeof (window.jQuery) === "undefined") ? jQuery : window.jQuery;  //NO I18N
                zgssearch.loadI18NJSFile(true);
            }
            else {
                zgssearch.network.loadSRIJSFile(zgssearch.GSConstant.gsjQueryURL, zgssearch.loadI18NJSFile);// Loading Ziasearch's jquery 3.6.0 file
            }
        };

        zgssearch.loadI18NJSFile = function (isJqExists) {
            if (!isJqExists) {
                var zsJquery = jQuery;
                window._jQueryGS = zsJquery.noConflict(true);
                window.jQuery = (typeof (window.jQuery) === "undefined") ? zsJquery : window.jQuery;  //NO I18N
                window.ZSJqueryCoreObj = {"scope": window._jQueryGS, "version": "3.6.0"}; //NO I18N
            }
            zgssearch.network.loadSRIJSFile(zgssearch.GSConstant.gsi18NJSURL, zgssearch.loadResultJsFiles);
        };

        zgssearch.loadSecurityEncryptFile = function (callback) {
            zgssearch.ZWAF_version = "7.3.3"; //NO I18N
            zgssearch.network.loadJSFile(window.location.protocol + "//" + zgssearch.GSConstant.STATIC_RESOURCE_SERVER + "/zohosecurity/v" + zgssearch.ZWAF_version + "/js/security-encryption.min.js",function () { //NO I18N
                    zgssearch.ZWAF = window.ZWAF[zgssearch.ZWAF_version];
                    zgssearch.ZWAF.configuration.setCSRF({
                        paramName: "conreqcsr", //NO I18N
                        cookieName: "CSRF_TOKEN" //NO I18N
                    });
                    zgssearch.ZWAF.Encryption.init({
                        scope: ZWAF.Encryption.SCOPES.ORG,
                        tag: "search_" + zgssearch.GSConstant.cuz, //NO I18N
                        preventCookieOverwrite: true,
                        handshakeURL: "/zgssearch/zwaf/encryption/handshake" //NO I18N
                    });
                    if (typeof callback === "function") {
                        callback();
                    }
                }
            );
        };

        zgssearch.loadResultJsFiles = function () {
            zgssearch.network.loadSRIJSFile(zgssearch.GSConstant.resultNewJSURL); //This will be calling once the bigger UI files loads
        };

        zgssearch.isArrayContain = function (value, array) {
            return (_jQueryGS.inArray(value, array) !== -1);
        };

        zgssearch.getCurrentLanguage = function(){
            var ulanguage = zgssearch.gscomponent.gslanguage || "en"; //NO I18N
            var ucountry = zgssearch.gscomponent.gscountry || ""; //NO I18N

            var urebrand = zgssearch.gscomponent.gsrebrand;
            urebrand = (urebrand == "baihui") ? urebrand : ""; //NO I18N

            if (zgssearch.GSConstant.supportedZSLanguages.indexOf(ulanguage) === -1) {
                if (zgssearch.GSConstant.languageVsCountryObj.hasOwnProperty(ulanguage)) {
                    var supportedRegions = zgssearch.GSConstant.languageVsCountryObj[ulanguage];
                    var supportedRegionSize = supportedRegions.length;
                    if (supportedRegionSize > 1) {
                        if(ucountry != ""){
                            let langCountry = (ucountry !== "") ? ulanguage + "_" + ucountry : ulanguage;
                            for(var i=0; i < supportedRegions.length; i++) {
                                if (supportedRegions[i].toLowerCase() === langCountry.toLowerCase()) {
                                    langCountry = supportedRegions[i];
                                }
                            }
                            ulanguage = langCountry != "" ? langCountry : "en";  //NO I18N
                        } else {
                            ulanguage = supportedRegions[0];
                        }
                    }
                    else {
                        ulanguage = supportedRegions[0];
                    }
                }
                else {
                    ulanguage = "en"; //NO I18N
                }
            }
            var langJSFilename = (urebrand ? urebrand + "_" : "") + ulanguage;
            return langJSFilename;
        };

        zgssearch.getLanguageFileName = function () {
            return "js/" + zgssearch.getCurrentLanguage() + ".js"; //NO I18N
        };

        zgssearch.loadZSFiles = function () {
            var gsbuildObj = zgssearch.gsbuildDetails || {};
            if (gsbuildObj.BUILD_DATE) {
                gsbuildObj.gslanguage = gsbuildObj.gslanguage || zgssearch.gscomponent.gslanguage;
                gsbuildObj.gscountry = gsbuildObj.gscountry || zgssearch.gscomponent.gscountry;
                gsbuildObj.gsserver = gsbuildObj.gsserver || "zohosearch"; //NO I18N
                /*gscomponent init*/
                zgssearch.gscomponent = Object.assign(zgssearch.gscomponent, gsbuildObj);
                zgssearch.GSConstant.BUILD_DATE = zgssearch.gscomponent.BUILD_DATE;
                zgssearch.GSConstant.STATIC_RESOURCE_SERVER = zgssearch.gscomponent.STATIC_RESOURCE_SERVER;

                gsbuildObj.gsjQueryURL = "js/jquery-3.6.0.min.js"; //NO I18N
                gsbuildObj.gsi18NJSURL = zgssearch.getLanguageFileName();
                if(zgssearch.gscomponent.UIType === 1) {
                    gsbuildObj.resultNewJSURL = "js/zsresult.js"; //NO I18N
                    gsbuildObj.resultNewCSSURL = "css/zsresult.css";  //NO I18N
                    // TO DO : Move to common flow when murphy enabling is applicable to all
                    zgssearch.loadMurphyFile();
                }
                else {
                    gsbuildObj.resultNewJSURL = "js/gsresult.js";  //NO I18N
                    gsbuildObj.resultNewCSSURL = zgssearch.isExtension ? "css/extresult.css" : "css/gsresult.css"; //NO I18N
                }
                zgssearch.setGSConstantObj(gsbuildObj);
                zgssearch.loadGSFile();
            }
        };

        zgssearch.loadWMSFiles = function () {
            zgssearch.network.loadSRICSSFile(wms_css_url,zgssearch.loadWMSJSFile);
        };

        zgssearch.loadWMSJSFile = function () {
            zgssearch.network.loadSRIJSFile(wms_js_url, zgssearch.registerWMS);
        };

        zgssearch.registerWMS = function () {
            var intervalStartTime = new Date().getTime();
            var wmsInit = setInterval(function () {
                if (new Date().getTime() - intervalStartTime > 60000) {
                    clearInterval(wmsInit);
                    return;
                }
                if (typeof WebMessanger !== 'undefined') {//No I18N
                    clearInterval(wmsInit);
                    WebMessanger.setClientSRIValues(wms_all_sri_values);
                    WebMessanger.setNoDomainChange();
                    if (rebrandName && rebrandName !== null && rebrandName !== "null") {//No I18N
                        WebMessanger.setRebrand(rebrandName);
                        WebMessanger.setIamServer(iamServer);
                        WebMessanger.setChatServer(chat_server_url); //file upload
                        WebMessanger.setPhotoServer(contacts_server_url); //photo url
                        WebMessanger.setMeetingUrl(meeting_server_url);//share desktop
                    }
                    WebMessanger.setLocale(user_info.language, user_info.country);
                    var settings = WMSSessionConfig.CHAT | WMSSessionConfig.CHAT_PRESENCE | WMSSessionConfig.PRESENCE_PERSONAL | WMSSessionConfig.CROSS_PRD | WMSSessionConfig.MP;
                    WebMessanger.setConfig(settings);
                    var serviceDirection = getComputedStyle(document.body).direction;
                    if(serviceDirection === "rtl") {
                        WebMessanger.enableRTLMode();
                    }
                    WebMessanger.registerZuid("SE", user_info.zuid, user_info.primary_email, zgssearch.isWMSSilentMode);//No I18N
                }
            }, 200);
        };


//        This function will give to service team to add in their code
//        This function will get version and domain info from WMS or service team
//        This function will load gshome.css and gshome.js
//        zgssearch.loadZGSHandler = function() {
//            var domscriptJquery = document.createElement('script');
//            domscriptJquery.type = "text/javascript";  //NO I18N
//            domscriptJquery.src = window.location.protocol + "//" + <js static server > + "/zohosearch/h1/js/gshandler.js?_T=" + new Date().getTime(); //NO I18N
//            domscriptJquery.onload = function() {
//Before calling this loadZGSHandler method ZiaSearch shoud be configured via gscomponent Object
//                zgssearch.initZGSHandler();
//            };
//            document.getElementsByTagName("head").item(0).appendChild(domscriptJquery);
//        };

        zgssearch.loadMurphyFile = function() {
            // Info : If the murphy is already installed in the parent domain overriding is restricted
            if (!(typeof (murphy) !== "undefined" && typeof (murphy) !== undefined &&  (murphy.hasOwnProperty("isMurphyInstalled") && murphy.isMurphyInstalled()))) {
                let appKey = zgssearch.gsbuildDetails.MURPHY_APP_KEY;
                let appDomain = zgssearch.gsbuildDetails.MURPHY_APP_DOMAIN;
                let authKey = zgssearch.gsbuildDetails.MURPHY_AUTH_KEY;
                if(appKey && appDomain && authKey) {
                    let murphyFilePath = zgssearch.network.getFingerPrintFilePath("js/murphy.min.js");  //NO I18N
                    zgssearch.network.loadJSFile(murphyFilePath, function() {
                        murphy.install({
                            config: {
                                "appKey": appKey, //NO I18N
                                "appDomain": appDomain, //NO I18N
                                "environment": "production", //NO I18N
                                "authKey": authKey, //NO I18N
                                "enableTracking": false, //NO I18N
                                "rageRequest": { //NO I18N
                                    "timeInterval": "5000", //NO I18N
                                    "tokenLimit": "3", //NO I18N
                                    "apiBasePath": "", //NO I18N
                                    "enable": true //NO I18N
                                }
                            },
                            setTags: function () {
                                return {
                                    "buildId": zgssearch.GSConstant.BUILD_DATE //NO I18N
                                    //"zuid": zgssearch.GSConstant.cuz //NO I18N
                                }
                            }
                        });
                    });
                }
            }
        };
        return zgssearch;
    })(zgssearch);
    window.zgssearch = zgssearch;
})(window);
