import requests
from requests.exceptions import ConnectionError
import json
# import pandas as pd
# import numpy as np
import re
import base64
# from datetime import date
from datetime import datetime
from time import sleep


class YandexDirectEcomru:
    def __init__(self, login=None, token=None, sandbox=False, use_operator_units='false'):
        self.login = login
        self.token = token
        self.client_id = None
        self.client_secret = None
        self.redirect_url = None

        urls = ['https://api.direct.yandex.ru/v4/json/',
                'https://api.direct.yandex.ru/live/v4/json/',
                'https://api.direct.yandex.com/json/v5/']

        sandbox_urls = ['https://api-sandbox.direct.yandex.ru/v4/json/',
                        'https://api-sandbox.direct.yandex.ru/live/v4/json/',
                        'https://api-sandbox.direct.yandex.com/json/v5/']

        self.head = {"Authorization": f'Bearer {self.token}',
                     "Accept-Language": "ru",
                     "Client-Login": self.login,
                     "Content-Type": "application/json; charset=utf-8",
                     "Use-Operator-Units": use_operator_units
                     }

        if sandbox is True:
            self.urls = sandbox_urls
        else:
            self.urls = urls

        self.counter = []  # счетчик запросов

    def get_auth_link(self, type_='token'):
        """
        Генерирует ссылку на страницу авторизации клиентом приложения
        """
        if type_ == 'token':
            return f'https://oauth.yandex.ru/authorize?response_type=token&client_id={self.client_id}'
        elif type_ == 'code':
            return f'https://oauth.yandex.ru/authorize?response_type=code&client_id={self.client_id}'
        else:
            print('Incorrect data')
            return None

    def get_token(self, code):
        """
        Получает токен по коду
        """
        url = 'https://oauth.yandex.ru/token'
        # url = f'https://oauth.yandex.ru/token?grant_type=authorization_code&code={code}&client_id={self.client_id}&client_secret={self.client_secret}'

        # head = {"Content-Type": "application/json; charset=utf-8"}
        head = {"Content-Type": "application/x-www-form-urlencoded"}

        # params = {'grant_type': 'authorization_code'}
        body = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret
                }
        response = requests.post(url, data=json.dumps(body))
        # response = requests.post(url, headers=head, data=json.dumps(body))
        # response = requests.post(url, headers=head, data=json.dumps(body, ensure_ascii=False).encode('utf8'))
        # response = requests.post(url, headers=head)
        # response = requests.post(url, params=body)
        print(response.status_code)
        # print(url)
        return response

    @staticmethod
    def u(x):
        """
        Вспомогательная функция кодировки
        """
        if type(x) == type(b''):
            return x.decode('utf8')
        else:
            return x

    def add_into_counter(self, response):
        """
        Функция для добавления данных в счетчик запросов
        """
        self.counter.append({'timestamp': str(datetime.now()),
                             'request_id': response.headers.get("RequestId", None),
                             'status_code': response.status_code,
                             'units': response.headers.get("Units", None)})

    @staticmethod
    def print_response_info(response):
        """
        Функция для вывода сообщений о ходе запроса
        """
        if response.status_code != 200 or response.json().get("error", False):
            print("Произошла ошибка при обращении к серверу API Директа.")
            print("Код ошибки: {}".format(response.json()["error"]["error_code"]))
            print("Описание ошибки: {}".format(YandexDirectEcomru.u(response.json()["error"]["error_detail"])))
            print("RequestId: {}".format(response.headers.get("RequestId", False)))
        else:
            print("RequestId: {}".format(response.headers.get("RequestId", False)))
            print("Информация о баллах: {}".format(response.headers.get("Units", False)))

    def exec_post_api5(self, service, headers, body):
        """
        Метод запроса к API5
        """
        try:
            response = requests.post(self.urls[2] + service, headers=headers,
                                     data=json.dumps(body, ensure_ascii=False).encode('utf8'))
            self.add_into_counter(response)
            self.print_response_info(response)
            return response
        except ConnectionError:
            print("Произошла ошибка соединения с сервером API.")
            return None
        except:
            print("Произошла непредвиденная ошибка.")
            return None

    def get_campaigns(self, criteries=None):
        """
        Возвращает параметры кампаний, отвечающих заданным критериям.
        Структура описания критериев:
        https://yandex.ru/dev/direct/doc/ref-v5/campaigns/get.html#input__CampaignsSelectionCriteria
        """
        if criteries is None:
            criteria = dict()
        else:
            criteria = criteries
        service = 'campaigns'
        body = {"method": "get",
                "params": {"SelectionCriteria": criteria,
                           "FieldNames": ["Id", "Name"]
                           }
                }
        return self.exec_post_api5(service, self.head, body)

    def get_groups(self, campaigns: list):
        """
        Возвращает параметры групп, отвечающих заданным критериям
        """
        service = 'adgroups'
        body = {"method": "get",
                "params": {"SelectionCriteria": {"CampaignIds": campaigns},
                           "FieldNames": ["Id", "Name", "Status", "Type"]}
                }
        return self.exec_post_api5(service, self.head, body)

    def create_new_wordstat_report(self, phrases, regions=None, lim=10):
        """
        Запускает на сервере формирование отчета о статистике поисковых запросов,
        возвращает идентификатор будущего отчета.
        """
        body = {"method": "CreateNewWordstatReport",
                "param": {"Phrases": phrases,
                          "GeoID": regions},
                "locale": "ru",
                "token": self.token}
        head = {"Accept-Language": "ru",
                "Content-Length": "204",
                "Content-Type": "application/json; charset=utf-8"}
        if len(phrases) <= lim:
            try:
                response = requests.post(self.urls[1], headers=head,
                                         data=json.dumps(body, ensure_ascii=False).encode('utf8'))
                self.add_into_counter(response)
                if response.status_code != 200 or response.json().get("error", False):
                    print("Произошла ошибка при обращении к серверу API Директа.")
                #                 print("Код ошибки: {}".format(response.json()["error"]["error_code"]))
                #                 print("Описание ошибки: {}".format(self.u(response.json()["error"]["error_detail"])))
                #                 print("RequestId: {}".format(response.headers.get("RequestId", False)))
                else:
                    print("RequestId: {}".format(response.headers.get("RequestId", False)))
                return response
            except ConnectionError:
                print("Произошла ошибка соединения с сервером API.")
                return None
            except:
                print("Произошла непредвиденная ошибка.")
                return None
        else:
            print('Превышен лимит фраз в одном запросе')
            return None

    def get_wordstat_report_list(self):
        """
        Возвращает список сформированных и формируемых отчетов о статистике поисковых запросов
        """
        body = {"method": "GetWordstatReportList",
                "token": self.token}
        try:
            response = requests.post(self.urls[1], data=json.dumps(body))
            self.add_into_counter(response)
            if response.status_code != 200 or response.json().get("error", False):
                print("Произошла ошибка при обращении к серверу API Директа.")
            #             print("Код ошибки: {}".format(response.json()["error"]["error_code"]))
            #             print("Описание ошибки: {}".format(self.u(response.json()["error"]["error_detail"])))
            #             print("RequestId: {}".format(response.headers.get("RequestId", False)))
            else:
                print("RequestId: {}".format(response.headers.get("RequestId", False)))
            return response
        except ConnectionError:
            print("Произошла ошибка соединения с сервером API.")
            return None
        except:
            print("Произошла непредвиденная ошибка.")
            return None

    def get_wordstat_report(self, report_id):
        """
        Возвращает отчет о статистике поисковых запросов
        """
        body = {"method": "GetWordstatReport",
                "param": int(report_id),
                "token": self.token}
        try:
            response = requests.post(self.urls[1], data=json.dumps(body))
            self.add_into_counter(response)
            if response.status_code != 200 or response.json().get("error", False):
                print("Произошла ошибка при обращении к серверу API Директа.")
            #             print("Код ошибки: {}".format(response.json()["error"]["error_code"]))
            #             print("Описание ошибки: {}".format(self.u(response.json()["error"]["error_detail"])))
            #             print("RequestId: {}".format(response.headers.get("RequestId", False)))
            else:
                print("RequestId: {}".format(response.headers.get("RequestId", False)))
            return response
        except ConnectionError:
            print("Произошла ошибка соединения с сервером API.")
            return None
        except:
            print("Произошла непредвиденная ошибка.")
            return None

    def delete_wordstat_report(self, report_id):
        """
        Удаляет отчет о статистике поисковых запросов
        """
        body = {"method": "DeleteWordstatReport",
                "param": int(report_id),
                "token": self.token}
        try:
            response = requests.post(self.urls[1], data=json.dumps(body))
            self.add_into_counter(response)
            if response.status_code != 200 or response.json().get("error", False):
                print("Произошла ошибка при обращении к серверу API Директа.")
            #             print("Код ошибки: {}".format(response.json()["error"]["error_code"]))
            #             print("Описание ошибки: {}".format(self.u(response.json()["error"]["error_detail"])))
            #             print("RequestId: {}".format(response.headers.get("RequestId", False)))
            else:
                print("RequestId: {}".format(response.headers.get("RequestId", False)))
            return response
        except ConnectionError:
            print("Произошла ошибка соединения с сервером API.")
            return None
        except:
            print("Произошла непредвиденная ошибка.")
            return None

    def create_new_forecast(self, phrases, regions=None, currency='RUB', auc_bids='No'):
        """
        Запускает на сервере формирование прогноза показов, кликов и затрат.
        Возможные значения currency: RUB, CHF, EUR, KZT, TRY, UAH, USD, BYN.
        """
        body = {"method": "CreateNewForecast",
                "param": {"Phrases": phrases,
                          "Categories": [],
                          "GeoID": regions,
                          "Currency": currency,
                          "AuctionBids": auc_bids},
                "locale": "ru",
                "token": self.token
                }
        head = {"Accept-Language": "ru",
                "Content-Length": "204",
                "Content-Type": "application/json; charset=utf-8"}
        try:
            response = requests.post(self.urls[1], data=json.dumps(body, ensure_ascii=False).encode('utf8'))
            self.add_into_counter(response)
            if response.status_code != 200 or response.json().get("error", False):
                print("Произошла ошибка при обращении к серверу API Директа.")
            #             print("Код ошибки: {}".format(response.json()["error"]["error_code"]))
            #             print("Описание ошибки: {}".format(self.u(response.json()["error"]["error_detail"])))
            #             print("RequestId: {}".format(response.headers.get("RequestId", False)))
            else:
                print("RequestId: {}".format(response.headers.get("RequestId", False)))
            return response
        except ConnectionError:
            print("Произошла ошибка соединения с сервером API.")
            return None
        except:
            print("Произошла непредвиденная ошибка.")
            return None

    def get_forecast_list(self):
        """
        Возвращает список сформированных и формируемых отчетов о прогнозируемом количестве
        показов и кликов, затратах на кампанию
        """
        body = {"method": "GetForecastList",
                "token": self.token}
        try:
            response = requests.post(self.urls[1], data=json.dumps(body))
            self.add_into_counter(response)
            if response.status_code != 200 or response.json().get("error", False):
                print("Произошла ошибка при обращении к серверу API Директа.")
            #             print("Код ошибки: {}".format(response.json()["error"]["error_code"]))
            #             print("Описание ошибки: {}".format(self.u(response.json()["error"]["error_detail"])))
            #             print("RequestId: {}".format(response.headers.get("RequestId", False)))
            else:
                print("RequestId: {}".format(response.headers.get("RequestId", False)))
            return response
        except ConnectionError:
            print("Произошла ошибка соединения с сервером API.")
            return None
        except:
            print("Произошла непредвиденная ошибка.")
            return None

    def get_forecast(self, forecast_id):
        """
        Возвращает сформированный прогноз показов, кликов и затрат по его идентификатору
        """
        body = {"method": "GetForecast",
                "param": int(forecast_id),
                "token": self.token
                }
        try:
            response = requests.post(self.urls[1], data=json.dumps(body))
            self.add_into_counter(response)
            if response.status_code != 200 or response.json().get("error", False):
                print("Произошла ошибка при обращении к серверу API Директа.")
            #             print("Код ошибки: {}".format(response.json()["error"]["error_code"]))
            #             print("Описание ошибки: {}".format(self.u(response.json()["error"]["error_detail"])))
            #             print("RequestId: {}".format(response.headers.get("RequestId", False)))
            else:
                print("RequestId: {}".format(response.headers.get("RequestId", False)))
            return response
        except ConnectionError:
            print("Произошла ошибка соединения с сервером API.")
            return None
        except:
            print("Произошла непредвиденная ошибка.")
            return None

    def delete_forecast_report(self, forecast_id):
        """
        Удаляет отчет о прогнозируемом количестве показов и кликов, затратах на кампанию
        """
        body = {"method": "DeleteForecastReport",
                "param": int(forecast_id),
                "token": self.token
                }
        try:
            response = requests.post(self.urls[1], data=json.dumps(body))
            self.add_into_counter(response)
            if response.status_code != 200 or response.json().get("error", False):
                print("Произошла ошибка при обращении к серверу API Директа.")
            #             print("Код ошибки: {}".format(response.json()["error"]["error_code"]))
            #             print("Описание ошибки: {}".format(self.u(response.json()["error"]["error_detail"])))
            #             print("RequestId: {}".format(response.headers.get("RequestId", False)))
            else:
                print("RequestId: {}".format(response.headers.get("RequestId", False)))
            return response
        except ConnectionError:
            print("Произошла ошибка соединения с сервером API.")
            return None
        except:
            print("Произошла непредвиденная ошибка.")
            return None

    @staticmethod
    def create_text_camp_params(s_bid_strat: str,
                                n_bid_strat: str,
                                s_weekly_spend_limit=None,
                                s_bid_ceiling=None,
                                s_goal_id=None,
                                s_average_cpc=None,
                                s_average_cpa=None,
                                s_reserve_return=None,
                                s_roi_coef=None,
                                s_profitability=None,
                                s_crr=None,
                                s_cpa=None,
                                n_limit_percent=100,
                                n_weekly_spend_limit=None,
                                n_bid_ceiling=None,
                                n_goal_id=None,
                                n_average_cpc=None,
                                n_average_cpa=None,
                                n_reserve_return=None,
                                n_roi_coef=None,
                                n_profitability=None,
                                n_crr=None,
                                n_cpa=None,
                                settings=None,
                                counter_ids=None,
                                #                                 rel_kw_budget_perc=None,
                                #                                 rel_kw_opt_goal_id=0,
                                goal_ids=None,
                                goal_vals=None,
                                attr_model="LYDC"
                                ):
        """
        Возвращает словарь с параметрами текстовой кампании
        """
        if settings is None:
            settings = [{"Option": "ADD_METRICA_TAG", "Value": "YES"},
                        {"Option": "ADD_OPENSTAT_TAG", "Value": "NO"},
                        {"Option": "ADD_TO_FAVORITES", "Value": "NO"},
                        {"Option": "ENABLE_AREA_OF_INTEREST_TARGETING", "Value": "YES"},
                        {"Option": "ENABLE_COMPANY_INFO", "Value": "YES"},
                        {"Option": "ENABLE_SITE_MONITORING", "Value": "NO"},
                        {"Option": "EXCLUDE_PAUSED_COMPETING_ADS", "Value": "NO"},
                        {"Option": "MAINTAIN_NETWORK_CPC", "Value": "NO"},
                        {"Option": "REQUIRE_SERVICING", "Value": "NO"},
                        {"Option": "CAMPAIGN_EXACT_PHRASE_MATCHING_ENABLED", "Value": "NO"}
                        ]
        result = {"TextCampaign": {"BiddingStrategy": {"Search": {},
                                                       "Network": {}}
                                   }}

        if settings is not None:
            result["TextCampaign"]["Settings"] = settings

        if counter_ids is not None:
            result["TextCampaign"]["CounterIds"] = {"Items": counter_ids}

        #         if rel_kw_budget_perc != None:
        #             result["TextCampaign"]["RelevantKeywords"] = {"BudgetPercent": rel_kw_budget_perc,
        #                                                           "OptimizeGoalId": rel_kw_opt_goal_id}
        if goal_ids is not None:
            try:
                goals = [{"GoalId": goal_id, "Value": goal_val * 1e6, "IsMetrikaSourceOfValue": "NO"} \
                         for goal_id, goal_val in zip(goal_ids, goal_vals)]
                result["TextCampaign"]["PriorityGoals"] = {"Items": goals}
            except TypeError:
                print(
                    'Не корректные параметры ключевых целей, на достижение которых направлена автоматическая корректировка ставок')

        if attr_model is not None:
            result["TextCampaign"]["AttributionModel"] = attr_model

        try:
            if s_bid_strat == 'HIGHEST_POSITION':
                result["TextCampaign"]["BiddingStrategy"]["Search"] = {"BiddingStrategyType": s_bid_strat}
            elif s_bid_strat == 'WB_MAXIMUM_CLICKS':
                if s_bid_ceiling is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Search"] = {"BiddingStrategyType": s_bid_strat,
                                                                           "WbMaximumClicks":
                                                                               {
                                                                                   'WeeklySpendLimit': s_weekly_spend_limit * 1e6,
                                                                                   'BidCeiling': s_bid_ceiling * 1e6}}
                else:
                    result["TextCampaign"]["BiddingStrategy"]["Search"] = {"BiddingStrategyType": s_bid_strat,
                                                                           "WbMaximumClicks":
                                                                               {
                                                                                   "WeeklySpendLimit": s_weekly_spend_limit * 1e6}}
            elif s_bid_strat == 'WB_MAXIMUM_CONVERSION_RATE':
                result["TextCampaign"]["BiddingStrategy"]["Search"] = {"BiddingStrategyType": s_bid_strat,
                                                                       "WbMaximumConversionRate": {
                                                                           "WeeklySpendLimit": s_weekly_spend_limit * 1e6,
                                                                           "GoalId": s_goal_id}}
                if s_bid_ceiling is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Search"]["WbMaximumConversionRate"].setdefault(
                        "BidCeiling",
                        s_bid_ceiling * 1e6)

            elif s_bid_strat == 'AVERAGE_CPC':
                result["TextCampaign"]["BiddingStrategy"]["Search"] = {"BiddingStrategyType": s_bid_strat,
                                                                       "AverageCpc": {
                                                                           "AverageCpc": s_average_cpc * 1e6}}
                if s_weekly_spend_limit is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Search"]["AverageCpc"].setdefault("WeeklySpendLimit",
                                                                                                 s_weekly_spend_limit * 1e6)
            elif s_bid_strat == 'AVERAGE_CPA':
                result["TextCampaign"]["BiddingStrategy"]["Search"] = {"BiddingStrategyType": s_bid_strat,
                                                                       "AverageCpa": {
                                                                           "AverageCpa": s_average_cpa * 1e6,
                                                                           "GoalId": s_goal_id}}
                if s_weekly_spend_limit is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Search"]["AverageCpa"].setdefault("WeeklySpendLimit",
                                                                                                 s_weekly_spend_limit * 1e6)

                if s_bid_ceiling is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Search"]["AverageCpa"].setdefault("BidCeiling",
                                                                                                 s_bid_ceiling * 1e6)
            elif s_bid_strat == 'AVERAGE_ROI':
                result["TextCampaign"]["BiddingStrategy"]["Search"] = {"BiddingStrategyType": s_bid_strat,
                                                                       "AverageRoi": {
                                                                           "ReserveReturn": s_reserve_return,
                                                                           "RoiCoef": s_roi_coef * 1e6,
                                                                           "GoalId": s_goal_id}}
                if s_weekly_spend_limit is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Search"]["AverageRoi"].setdefault("WeeklySpendLimit",
                                                                                                 s_weekly_spend_limit * 1e6)
                if s_bid_ceiling is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Search"]["AverageRoi"].setdefault("BidCeiling",
                                                                                                 s_bid_ceiling * 1e6)
                if s_profitability is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Search"]["AverageRoi"].setdefault("Profitability",
                                                                                                 s_profitability * 1e6)
            elif s_bid_strat == 'AVERAGE_CRR':
                result["TextCampaign"]["BiddingStrategy"]["Search"] = {"BiddingStrategyType": s_bid_strat,
                                                                       "AverageCrr": {
                                                                           "Crr": s_crr,
                                                                           "GoalId": s_goal_id}}
                if s_weekly_spend_limit is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Search"]["AverageCrr"].setdefault("WeeklySpendLimit",
                                                                                                 s_weekly_spend_limit * 1e6)
            elif s_bid_strat == 'PAY_FOR_CONVERSION':
                result["TextCampaign"]["BiddingStrategy"]["Search"] = {"BiddingStrategyType": s_bid_strat,
                                                                       "PayForConversion": {
                                                                           "Cpa": s_cpa * 1e6,
                                                                           "GoalId": s_goal_id}}
                if s_weekly_spend_limit is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Search"]["PayForConversion"].setdefault(
                        "WeeklySpendLimit",
                        s_weekly_spend_limit * 1e6)
            elif s_bid_strat == 'PAY_FOR_CONVERSION_CRR':
                result["TextCampaign"]["BiddingStrategy"]["Search"] = {"BiddingStrategyType": s_bid_strat,
                                                                       "PayForConversionCrr": {
                                                                           "Crr": s_crr,
                                                                           "GoalId": s_goal_id}}
                if s_weekly_spend_limit is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Search"]["PayForConversionCrr"].setdefault(
                        "WeeklySpendLimit",
                        s_weekly_spend_limit * 1e6)
            elif s_bid_strat == 'SERVING_OFF':
                result["TextCampaign"]["BiddingStrategy"]["Search"] = {"BiddingStrategyType": s_bid_strat}
        except TypeError:
            print('Не корректные параметры стратегии показа на поиске')
            return None

        try:
            if n_bid_strat == 'NETWORK_DEFAULT':
                if s_bid_strat == 'HIGHEST_POSITION':
                    result["TextCampaign"]["BiddingStrategy"]["Network"] = {"BiddingStrategyType": n_bid_strat,
                                                                            "NetworkDefault": {
                                                                                "LimitPercent": n_limit_percent}}
                else:
                    result["TextCampaign"]["BiddingStrategy"]["Network"] = {"BiddingStrategyType": n_bid_strat,
                                                                            "NetworkDefault": {}}
            elif n_bid_strat == 'MAXIMUM_COVERAGE':
                result["TextCampaign"]["BiddingStrategy"]["Network"] = {"BiddingStrategyType": n_bid_strat}
            elif n_bid_strat == 'WB_MAXIMUM_CLICKS':
                result["TextCampaign"]["BiddingStrategy"]["Network"] = {"BiddingStrategyType": n_bid_strat,
                                                                        "WbMaximumClicks": {
                                                                            "WeeklySpendLimit": n_weekly_spend_limit * 1e6}}
                if n_bid_ceiling is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Network"]["WbMaximumClicks"].setdefault("BidCeiling",
                                                                                                       n_bid_ceiling * 1e6)
            elif n_bid_strat == 'WB_MAXIMUM_CONVERSION_RATE':
                result["TextCampaign"]["BiddingStrategy"]["Network"] = {"BiddingStrategyType": n_bid_strat,
                                                                        "WbMaximumConversionRate": {
                                                                            "WeeklySpendLimit": n_weekly_spend_limit * 1e6,
                                                                            "GoalId": n_goal_id}}
                if n_bid_ceiling is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Network"]["WbMaximumConversionRate"].setdefault(
                        "BidCeiling",
                        n_bid_ceiling * 1e6)
            elif n_bid_strat == 'AVERAGE_CPC':
                result["TextCampaign"]["BiddingStrategy"]["Network"] = {"BiddingStrategyType": n_bid_strat,
                                                                        "AverageCpc": {
                                                                            "AverageCpc": n_average_cpc * 1e6}}
                if n_weekly_spend_limit is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Network"]["AverageCpc"].setdefault("WeeklySpendLimit",
                                                                                                  n_weekly_spend_limit * 1e6)
            elif n_bid_strat == 'AVERAGE_CPA':
                result["TextCampaign"]["BiddingStrategy"]["Network"] = {"BiddingStrategyType": n_bid_strat,
                                                                        "AverageCpa": {
                                                                            "AverageCpa": n_average_cpa * 1e6,
                                                                            "GoalId": n_goal_id}}
                if n_weekly_spend_limit is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Network"]["AverageCpa"].setdefault("WeeklySpendLimit",
                                                                                                  n_weekly_spend_limit * 1e6)
                if n_bid_ceiling is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Network"]["AverageCpa"].setdefault("BidCeiling",
                                                                                                  n_bid_ceiling * 1e6)
            elif n_bid_strat == 'AVERAGE_ROI':
                result["TextCampaign"]["BiddingStrategy"]["Network"] = {"BiddingStrategyType": n_bid_strat,
                                                                        "AverageRoi": {
                                                                            "ReserveReturn": n_reserve_return,
                                                                            "RoiCoef": n_roi_coef * 1e6,
                                                                            "GoalId": n_goal_id}}
                if n_weekly_spend_limit is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Network"]["AverageRoi"].setdefault("WeeklySpendLimit",
                                                                                                  n_weekly_spend_limit * 1e6)
                if n_bid_ceiling is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Network"]["AverageRoi"].setdefault("BidCeiling",
                                                                                                  n_bid_ceiling * 1e6)
                if n_profitability is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Network"]["AverageRoi"].setdefault("Profitability",
                                                                                                  n_profitability * 1e6)
            elif n_bid_strat == 'AVERAGE_CRR':
                result["TextCampaign"]["BiddingStrategy"]["Network"] = {"BiddingStrategyType": n_bid_strat,
                                                                        "AverageCrr": {
                                                                            "Crr": n_crr,
                                                                            "GoalId": n_goal_id}}
                if n_weekly_spend_limit is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Network"]["AverageCrr"].setdefault("WeeklySpendLimit",
                                                                                                  n_weekly_spend_limit * 1e6)
            elif n_bid_strat == 'PAY_FOR_CONVERSION':
                result["TextCampaign"]["BiddingStrategy"]["Network"] = {"BiddingStrategyType": n_bid_strat,
                                                                        "PayForConversion": {
                                                                            "Cpa": n_cpa * 1e6,
                                                                            "GoalId": n_goal_id}}
                if n_weekly_spend_limit is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Network"]["PayForConversion"].setdefault(
                        "WeeklySpendLimit",
                        n_weekly_spend_limit * 1e6)
            elif n_bid_strat == 'PAY_FOR_CONVERSION_CRR':
                result["TextCampaign"]["BiddingStrategy"]["Network"] = {"BiddingStrategyType": n_bid_strat,
                                                                        "PayForConversionCrr": {
                                                                            "Crr": n_crr,
                                                                            "GoalId": n_goal_id}}
                if n_weekly_spend_limit is not None:
                    result["TextCampaign"]["BiddingStrategy"]["Network"]["PayForConversionCrr"].setdefault(
                        "WeeklySpendLimit",
                        n_weekly_spend_limit * 1e6)
            elif n_bid_strat == 'SERVING_OFF':
                result["TextCampaign"]["BiddingStrategy"]["Network"] = {"BiddingStrategyType": n_bid_strat}
        except TypeError:
            print('Не корректные параметры стратегии показа в сетях')
            return None

        return result

    @staticmethod
    def create_campaign(name: str,
                        start_date: str,
                        end_date=None,
                        client_info=None,
                        sms_events=None,
                        sms_time_from="9:00",
                        sms_time_to="21:00",
                        email=None,
                        email_ch_pos_interval=60,
                        email_warning_bal=20,
                        email_send_acc_news="NO",
                        email_send_warnings="NO",
                        timezone="Europe/Moscow",
                        daily_budget_amount=None,
                        daily_budget_mode=None,
                        negative_keywords=None,
                        blocked_ips=None,
                        excluded_sites=None,
                        text_campaign_params=None,
                        mobile_app_campaign_params=None,
                        dynamic_text_campaign_params=None,
                        cpm_banner_campaign_params=None,
                        smart_campaign_params=None,
                        time_targeting_shedule=None,
                        time_targeting_cons_working_weekends=None,
                        time_targeting_suspend_on_holidays=None,
                        time_targeting_bid_percent=None,
                        time_targeting_start_hour=None,
                        time_targeting_end_hour=None
                        ):
        """
        Возвращает словарь с параметрами кампании
        """
        result = {"Name": name,
                  "StartDate": start_date}

        if client_info is not None:
            result["ClientInfo"] = client_info

        if sms_events is not None:
            result.setdefault("Notification", {})
            result["Notification"].setdefault("SmsSettings", {})
            result["Notification"]["SmsSettings"] = {"Events": sms_events,
                                                     "TimeFrom": sms_time_from,
                                                     "TimeTo": sms_time_to}
        if email is not None:
            result.setdefault("Notification", {})
            result["Notification"].setdefault("EmailSettings", {})
            result["Notification"]["EmailSettings"] = {"Email": email,
                                                       "CheckPositionInterval": email_ch_pos_interval,
                                                       "WarningBalance": email_warning_bal,
                                                       "SendAccountNews": email_send_acc_news,
                                                       "SendWarnings": email_send_warnings}

        if timezone is not None:
            result["TimeZone"] = timezone

        if daily_budget_amount is not None and daily_budget_mode is not None:
            result["DailyBudget"] = {"Amount": daily_budget_amount * 1e6,
                                     "Mode": daily_budget_mode}

        if end_date is not None:
            result["EndDate"] = end_date

        if negative_keywords is not None:
            result["NegativeKeywords"] = {"Items": negative_keywords}

        if blocked_ips is not None:
            if len(blocked_ips) <= 25:
                result["BlockedIps"] = {"Items": blocked_ips}
            else:
                print('Количество blocked_ips превышает максимальное значение')

        if excluded_sites is not None:
            if len(excluded_sites) <= 1000:
                for site in excluded_sites:
                    if len(site) > 255:
                        print('Длина строки excluded_site превышает максимальное значение')
                        return None
                        # break
                result["ExcludedSites"] = excluded_sites
            else:
                print('Количество excluded_sites превышает максимальное значение')

        if text_campaign_params is not None:
            result["TextCampaign"] = text_campaign_params
        elif mobile_app_campaign_params is not None:
            result["MobileAppCampaign"] = mobile_app_campaign_params
        elif dynamic_text_campaign_params is not None:
            result["DynamicTextCampaign"] = dynamic_text_campaign_params
        elif cpm_banner_campaign_params is not None:
            result["CpmBannerCampaign"] = cpm_banner_campaign_params
        elif smart_campaign_params is not None:
            result["SmartCampaign"] = smart_campaign_params

        if time_targeting_shedule is not None:
            result.setdefault("TimeTargeting", {})
            result["TimeTargeting"]["Schedule"] = {"Items": time_targeting_shedule}

        if time_targeting_cons_working_weekends is not None:
            result.setdefault("TimeTargeting", {})
            result["TimeTargeting"]["ConsiderWorkingWeekends"] = time_targeting_cons_working_weekends

        if time_targeting_suspend_on_holidays is not None:
            result.setdefault("TimeTargeting", {})
            if time_targeting_suspend_on_holidays == "YES":
                result["TimeTargeting"]["HolidaysSchedule"] = {"SuspendOnHolidays": time_targeting_suspend_on_holidays}
            elif time_targeting_suspend_on_holidays == "NO":
                result["TimeTargeting"]["HolidaysSchedule"] = {"SuspendOnHolidays": time_targeting_suspend_on_holidays,
                                                               "BidPercent": time_targeting_bid_percent,
                                                               "StartHour": time_targeting_start_hour,
                                                               "EndHour": time_targeting_end_hour}
        return result

    def add_camp(self, campaigns: list):
        """
        Создает кампании
        """
        service = 'campaigns'
        body = {"method": "add",
                "params": {"Campaigns": campaigns}
                }
        return self.exec_post_api5(service, self.head, body)

    def manage_camps(self, campaigns: list, action: str):
        """
        Удаляет, архивирует/разархивирует, останавливает/возобновляет показы кампании
        (delete, archive, unarchive, suspend, resume)
        """
        service = 'campaigns'
        body = {"method": action,
                "params": {"SelectionCriteria": {"Ids": campaigns}}
                }
        return self.exec_post_api5(service, self.head, body)

    def get_stat_goals(self, campaigns: list):
        """
        Возвращает сведения о целях Яндекс Метрики, которые доступны для кампании
        """
        body = {"method": "GetStatGoals",
                "param": {"CampaignIDS": campaigns},
                "locale": "ru",
                "token": self.token
                }
        head = {"Accept-Language": "ru",
                "Content-Length": "204",
                "Content-Type": "application/json; charset=utf-8"}

        response = requests.post(self.urls[1],
                                 data=json.dumps(body, ensure_ascii=False).encode('utf8'))
        self.add_into_counter(response)
        self.print_response_info(response)
        return response

    def dictionaries(self, dict_names: list):
        """
        Возвращает справочные данные: регионы, часовые пояса, курсы валют,
        список станций метрополитена, ограничения на значения параметров, внешние сети (SSP),
        сегменты Крипты для нацеливания по профилю пользователя и др.
        ( "Currencies" | "MetroStations" | "GeoRegions" | "TimeZones" | "Constants" | "AdCategories" |
        "OperationSystemVersions" | "ProductivityAssertions" | "SupplySidePlatforms" | "Interests" |
        "AudienceCriteriaTypes" | "AudienceDemographicProfiles" | "AudienceInterests" | "FilterSchemas")
        """
        service = 'dictionaries'
        body = {"method": "get",
                "params": {"DictionaryNames": dict_names}
                }
        return self.exec_post_api5(service, self.head, body)

    @staticmethod
    def create_group(name: str,
                     campaign_id: int,
                     region_ids: list,
                     negative_keywords=None,
                     negative_keyword_set_ids=None,
                     tracking_params=None,
                     text_feed_id=None,
                     text_feed_category_ids=None
                     ):
        """
        Возвращает словарь с параметрами группы
        """
        result = {"Name": name,
                  "CampaignId": campaign_id,
                  "RegionIds": region_ids
                  }

        if negative_keywords is not None:
            if len(''.join(re.findall(r'\w', ''.join(negative_keywords)))) > 64:
                print(f'Не корректная cуммарная длина минус-фраз в массиве')
                return None
            else:
                for phrase in negative_keywords:
                    if len(phrase.split(' ')) > 7:
                        print(f'Не корректная длина минус-фразы {phrase}')
                        return None
                    else:
                        for word in phrase.split(' '):
                            if len(word) > 35:
                                print(f'Не корректная длина слова {word} минус-фразы {phrase}')
                                return None
            result["NegativeKeywords"] = {"Items": negative_keywords}

        if negative_keyword_set_ids is not None:
            if len(negative_keyword_set_ids) <= 3:
                result["NegativeKeywordSharedSetIds"] = {"Items": negative_keyword_set_ids}
            else:
                print('Длина negative_keyword_set_ids более 3')
                return None

        if tracking_params is not None:
            if len(tracking_params) <= 1024:
                result["TrackingParams"] = tracking_params
            else:
                print('Длина tracking_params более 1024 символов')
                return None

        if text_feed_id is not None:
            result["TextAdGroupFeedParams"] = {"FeedId": text_feed_id}
            if text_feed_category_ids is not None:
                result["TextAdGroupFeedParams"].setdefault("FeedCategoryIds", {"Items": text_feed_category_ids})

        return result

    def add_groups(self, groups: list):
        """
        Создает группы объявлений
        """
        service = 'adgroups'
        body = {"method": "add",
                "params": {"AdGroups": groups}
                }
        return self.exec_post_api5(service, self.head, body)

    def delete_groups(self, groups: list):
        """
        Удаляет группы объявлений
        """
        service = 'adgroups'
        body = {"method": "delete",
                "params": {"SelectionCriteria": {"Ids": groups}}
                }
        return self.exec_post_api5(service, self.head, body)

    @staticmethod
    def create_sitelink(title: str,
                        href=None,
                        turbopage_id=None,
                        description=None
                        ):
        """
        Возвращает словарь со структурой быстрой ссылки
        """
        result = {}

        if len(title) <= 30:
            result = {"Title": title}
        else:
            print('Длина текста быстрой ссылки превышает 30 символов')
            return None

        if href is not None:
            if len(href) <= 1024:
                result["Href"] = href
            else:
                print('Длина ссылки превышает 1024 символов')
                return None

        if turbopage_id is not None:
            result["TurboPageId"] = turbopage_id

        if description is not None:
            if len(description) <= 60:
                result["Description"] = description
            else:
                print('Длина описания превышает 60 символов')
                return None

        return result

    @staticmethod
    def create_sitelinks_set(sitelinks: list):
        """
        Возвращает набор быстрых ссылок
        """
        if len(sitelinks) > 8:
            print('Количество быстрых ссылок превышает 8')
            return None

        titles = [sitelink["Title"] for sitelink in sitelinks]
        sum_lenght_1 = 0
        sum_lenght_2 = 0
        if len(titles) <= 4:
            for title in titles:
                sum_lenght_1 += len(title)
        else:
            for title in titles[:4]:
                sum_lenght_1 += len(title)
            for title in titles[4:]:
                sum_lenght_2 += len(title)
        if sum_lenght_1 > 66 or sum_lenght_2 > 66:
            print('Превышшена суммарная длина текстов быстрых ссылок')
            return None
        else:
            return {"Sitelinks": sitelinks}

    def add_sitelinks(self, sitelinks_sets: list):
        """
        Создает наборы быстрых ссылок
        """
        service = 'sitelinks'
        body = {"method": "add",
                "params": {"SitelinksSets": sitelinks_sets}
                }
        return self.exec_post_api5(service, self.head, body)

    def delete_sitelinks(self, sitelinks_sets: list):
        """
        Удаляет наборы быстрых ссылок
        """
        service = 'sitelinks'
        body = {"method": "delete",
                "params": {"SelectionCriteria": {"Ids": sitelinks_sets}}
                }
        return self.exec_post_api5(service, self.head, body)

    def get_sitelinks(self, sitelinks_sets_ids=None):
        """
        Возвращает наборы быстрых ссылок, отвечающие заданным критериям
        """
        service = 'sitelinks'
        body = {"method": "get",
                "params": {"SelectionCriteria": {}
                           #                            "FieldNames": [( "Id" | "Sitelinks" ), ... ],
                           #                            "SitelinkFieldNames": [( "Title" | "Href" | "Description" | "TurboPageId" ), ... ],
                           #                            "Page": {"Limit": (long),
                           #                                     "Offset": (long)}
                           }
                }
        if sitelinks_sets_ids is not None:
            body["params"]["SelectionCriteria"] = {"Ids": sitelinks_sets_ids}
        else:
            body["params"]["SelectionCriteria"] = {}

        return self.exec_post_api5(service, self.head, body)

    @staticmethod
    def create_ad_params(ads_group_id: int,
                         txt_ad_title=None,
                         txt_ad_title2=None,
                         txt_ad_text=None,
                         txt_mobile=None,
                         href=None,
                         turbo_page_id=None,
                         vcard_id=None,
                         business_id=None,
                         prefer_vcard_over_business=None,
                         txt_ad_image_hash=None,
                         sitelink_set_id=None,
                         txt_display_url_path=None,
                         ad_extension_ids=None,
                         creative_id=None,
                         txt_price=None,
                         txt_old_price=None,
                         txt_price_qualifier=None,
                         txt_price_currency=None
                         ):
        """
        Возвращает словарь с параметрами объявления
        """
        result = {"AdGroupId": ads_group_id}

        if txt_ad_title is not None and txt_ad_text is not None and txt_mobile is not None:
            if len(txt_ad_title) > 56:
                print('Превышена суммарная длина заголовка1 (56 символов)')
                return None
            else:
                for word in txt_ad_title.split(' '):
                    if len(word) > 22:
                        print(f'Превышена длина слова {word} заголовка1 (22 символа)')
                        return None
            result["TextAd"] = {"Title": txt_ad_title}

            if txt_ad_title2 is not None:
                if (len(re.findall(r'[^!,.;:"]', txt_ad_title2)) > 30 or
                        len(re.findall(r'[!,.;:"]', txt_ad_title2)) > 15):
                    print('Не корректная длина заголовка2')
                    return None
                else:
                    for word in txt_ad_title2.split(' '):
                        if len(word) > 22:
                            print(f'Превышена длина слова {word} заголовка2 (22 символа)')
                            return None
                result["TextAd"].setdefault("Title2", txt_ad_title2)

            if (len(re.findall(r'[^!,.;:"]', txt_ad_text)) > 81 or
                    len(re.findall(r'[!,.;:"]', txt_ad_text)) > 15):
                print('Не корректная длина текста объявления')
                return None
            else:
                for word in txt_ad_text.split(' '):
                    if len(word) > 23:
                        print(f'Превышена длина слова {word} текста объявления (23 символа)')
                        return None
            result["TextAd"].setdefault("Text", txt_ad_text)
            result["TextAd"].setdefault("Mobile", txt_mobile)

            if href is not None:
                if len(href) > 1024:
                    print('Длина ссылки более 1024 символов')
                    return None
                else:
                    result["TextAd"].setdefault("Href", href)

            if turbo_page_id is not None:
                result["TextAd"].setdefault("TurboPageId", turbo_page_id)

            if vcard_id is not None:
                result["TextAd"].setdefault("VCardId", vcard_id)

            if business_id is not None:
                result["TextAd"].setdefault("BusinessId", business_id)

            if vcard_id is not None and business_id is not None:
                result["TextAd"].setdefault("PreferVCardOverBusiness", prefer_vcard_over_business)
            elif (vcard_id is not None and business_id is None) or (vcard_id is None and business_id is not None):
                result["TextAd"].setdefault("PreferVCardOverBusiness", "NO")

            if txt_ad_image_hash is not None:
                result["TextAd"].setdefault("AdImageHash", txt_ad_image_hash)

            if (href is not None or turbo_page_id is not None) and sitelink_set_id is not None:
                result["TextAd"].setdefault("SitelinkSetId", sitelink_set_id)

            if href is not None and txt_display_url_path is not None:
                if (len(txt_display_url_path) > 20 or
                        (' ' in txt_display_url_path) or
                        ('_' in txt_display_url_path) or
                        ('--' in txt_display_url_path) or
                        ('//' in txt_display_url_path)):
                    print('Не корректная отображаемая ссылка')
                    return None
                else:
                    result["TextAd"].setdefault("DisplayUrlPath", txt_display_url_path)

            if ad_extension_ids is not None:
                if len(ad_extension_ids) > 50:
                    print('Длина массива идентификаторов расширений превышает 50')
                    return None
                else:
                    result["TextAd"].setdefault("AdExtensionIds", ad_extension_ids)

            if creative_id is not None:
                result["TextAd"].setdefault("VideoExtension", {"CreativeId": creative_id})

            if txt_price is not None and txt_price_qualifier is not None and txt_price_currency is not None:
                result["TextAd"].setdefault("PriceExtension", {"Price": txt_price * 1e6,
                                                               "PriceQualifier": txt_price_qualifier,
                                                               "PriceCurrency": txt_price_currency})
                if txt_old_price != None:
                    if txt_old_price > txt_price:
                        result["TextAd"]["PriceExtension"].setdefault("OldPrice", txt_old_price * 1e6)
        return result

    def add_ads(self, ads: list):
        """
        Создает объявления
        """
        service = 'ads'
        body = {"method": "add",
                "params": {"Ads": ads}
                }
        return self.exec_post_api5(service, self.head, body)

    def get_ads(self, ids=None, groups=None, campaigns=None):
        """
        Возвращает параметры объявлений, отвечающих заданным критериям
        """
        service = 'ads'
        body = {"method": "get",
                "params": {"SelectionCriteria": {
                    #                     "Ids": ids,
                    #                     "AdGroupIds": groups,
                    #                     "CampaignIds": campaigns
                },
                    "FieldNames": ["AdCategories", "AgeLabel", "AdGroupId", "CampaignId", "Id", "State",
                                   "Status", "StatusClarification", "Type", "Subtype"]
                }
                }
        if ids is not None:
            if len(ids) > 10000:
                print('Количество кампаний превышает 10000')
                return None
            else:
                body["params"]["SelectionCriteria"].setdefault("Ids", ids)

        if groups is not None:
            if len(groups) > 1000:
                print('Количество групп превышает 1000')
                return None
            else:
                body["params"]["SelectionCriteria"].setdefault("AdGroupIds", groups)

        if campaigns is not None:
            if len(campaigns) > 10:
                print('Количество кампаний превышает 10')
                return None
            else:
                body["params"]["SelectionCriteria"].setdefault("CampaignIds", campaigns)

        return self.exec_post_api5(service, self.head, body)

    def manage_ads(self, ids: list, action: str):
        """
        Удаляет, архивирует/разархивирует, останавливает/возобновляет показы объявлений
        (delete, archive, unarchive, suspend, resume)
        """
        service = 'ads'
        body = {"method": action,
                "params": {"SelectionCriteria": {"Ids": ids}}
                }

        return self.exec_post_api5(service, self.head, body)

    def add_images(self, image_data_list, names_list, lim=3):
        """
        Выполняет синхронную загрузку изображений в виде бинарных данных
        """
        if len(names_list) > lim:
            print('Количество изображений превышает ограничение')
            return None
        else:
            images = [{"ImageData": data.decode('utf8'), "Name": name} for data, name in
                      zip(image_data_list, names_list)]
        #             print(images)
        service = 'adimages'
        body = {"method": "add",
                "params": {"AdImages": images}}

        return self.exec_post_api5(service, self.head, body)

    @staticmethod
    def img_convert(img_path: str):
        """
        Конвертирует изображение в base64
        """
        with open(img_path, "rb") as image_file:
            #             encoded_string = base64.encodestring(image_file.read())
            encoded_string = base64.b64encode(image_file.read())
        #         return encoded_string.encode('utf8')
        return encoded_string

    def get_images(self,
                   field_names=None,
                   ad_image_hashes=None,
                   associated=None,
                   limit=None,
                   offset=None):
        """
        Возвращает изображения, отвечающие заданным критериям
        """
        service = 'adimages'
        body = {"method": "get",
                "params": {"FieldNames": field_names}
                }
        if ad_image_hashes is not None:
            body["params"].setdefault("SelectionCriteria", {})
            body["params"]["SelectionCriteria"].setdefault("AdImageHashes", ad_image_hashes)
        if associated is not None:
            body["params"].setdefault("SelectionCriteria", {})
            body["params"]["SelectionCriteria"].setdefault("Associated", associated)
        if limit is not None:
            body["params"].setdefault("Page", {})
            body["params"]["Page"].setdefault("Limit", limit)
            if offset is not None:
                #                 body["params"].setdefault("Page", {})
                body["params"]["Page"].setdefault("Offset", offset)
        #         print(body)

        return self.exec_post_api5(service, self.head, body)

    @staticmethod
    def get_field_names(report_type):
        """
        Выводит список всех возможных полей для отчета в зависимости от его типа
        https://yandex.ru/dev/direct/doc/reports/fields-list.html
        """
        field_names = []
        if report_type == 'ACCOUNT_PERFORMANCE_REPORT':
            field_names = ['AdFormat', 'AdNetworkType', 'Age', 'AvgClickPosition', 'AvgCpc', 'AvgEffectiveBid',
                           'AvgImpressionPosition', 'AvgPageviews', 'AvgTrafficVolume',
                           'BounceRate', 'Bounces',
                           'CampaignType', 'CarrierType', 'Clicks', 'ClientLogin', 'ConversionRate',
                           'Conversions', 'Cost', 'CostPerConversion', 'CriterionType', 'Ctr',
                           'Date', 'Device',
                           'ExternalNetworkName',
                           'Gender', 'GoalsRoi',
                           'Impressions', 'IncomeGrade',
                           'LocationOfPresenceId', 'LocationOfPresenceName',
                           'MatchType', 'MobilePlatform',
                           'Placement', 'Profit',
                           'Revenue',
                           'Sessions', 'Slot',
                           'TargetingCategory', 'TargetingLocationId', 'TargetingLocationName',
                           'WeightedCtr', 'WeightedImpressions']
        #             excluded: ['ClickType', 'CriteriaType', 'Month', 'Quarter', 'Week', 'Year']

        elif report_type == 'AD_PERFORMANCE_REPORT':
            field_names = ['AdFormat', 'AdGroupId', 'AdGroupName', 'AdId', 'AdNetworkType', 'Age',
                           'AvgClickPosition', 'AvgCpc', 'AvgEffectiveBid',
                           'AvgImpressionPosition', 'AvgPageviews', 'AvgTrafficVolume',
                           'BounceRate', 'Bounces',
                           'CampaignId', 'CampaignName', 'CampaignUrlPath', 'CampaignType', 'CarrierType', 'Clicks',
                           'ClientLogin', 'ConversionRate', 'Conversions', 'Cost', 'CostPerConversion',
                           'CriterionType', 'Ctr',
                           'Date', 'Device',
                           'ExternalNetworkName',
                           'Gender', 'GoalsRoi',
                           'Impressions', 'IncomeGrade',
                           'LocationOfPresenceId', 'LocationOfPresenceName',
                           'MatchType', 'MobilePlatform',
                           'Placement', 'Profit',
                           'Revenue',
                           'Sessions', 'Slot',
                           'TargetingCategory', 'TargetingLocationId', 'TargetingLocationName',
                           'WeightedCtr', 'WeightedImpressions']
        #             excluded: ['CriteriaType', 'ClickType', 'Month', 'Quarter', 'Week', 'Year']

        elif report_type == 'ADGROUP_PERFORMANCE_REPORT':
            field_names = ['AdFormat', 'AdGroupId', 'AdGroupName', 'AdNetworkType', 'Age',
                           'AvgClickPosition', 'AvgCpc', 'AvgEffectiveBid',
                           'AvgImpressionPosition', 'AvgPageviews', 'AvgTrafficVolume',
                           'BounceRate', 'Bounces',
                           'CampaignId', 'CampaignName', 'CampaignUrlPath', 'CampaignType', 'CarrierType', 'Clicks',
                           'ClientLogin', 'ConversionRate', 'Conversions', 'Cost', 'CostPerConversion',
                           'CriterionType', 'Ctr',
                           'Date', 'Device',
                           'ExternalNetworkName',
                           'Gender', 'GoalsRoi',
                           'Impressions', 'IncomeGrade',
                           'LocationOfPresenceId', 'LocationOfPresenceName',
                           'MatchType', 'MobilePlatform',
                           'Placement', 'Profit',
                           'Revenue',
                           'Sessions', 'Slot',
                           'TargetingCategory', 'TargetingLocationId', 'TargetingLocationName',
                           'WeightedCtr', 'WeightedImpressions']
        #             excluded: ['ClickType', 'CriteriaType', 'ImpressionShare', 'Month', 'Quarter', 'Week', 'Year']

        elif report_type == 'CAMPAIGN_PERFORMANCE_REPORT':
            field_names = ['AdFormat', 'AdNetworkType', 'Age', 'AvgClickPosition', 'AvgCpc', 'AvgEffectiveBid',
                           'AvgImpressionPosition', 'AvgPageviews', 'AvgTrafficVolume',
                           'BounceRate', 'Bounces',
                           'CampaignId', 'CampaignName', 'CampaignUrlPath', 'CampaignType', 'CarrierType', 'Clicks',
                           'ClientLogin', 'ConversionRate', 'Conversions', 'Cost', 'CostPerConversion',
                           'CriterionType', 'Ctr',
                           'Date', 'Device',
                           'ExternalNetworkName',
                           'Gender', 'GoalsRoi',
                           'Impressions', 'IncomeGrade',
                           'LocationOfPresenceId', 'LocationOfPresenceName',
                           'MatchType', 'MobilePlatform',
                           'Placement', 'Profit',
                           'Revenue',
                           'Sessions', 'Slot',
                           'TargetingCategory', 'TargetingLocationId', 'TargetingLocationName',
                           'WeightedCtr', 'WeightedImpressions']
        #             excluded: ['ClickType', 'CriteriaType', 'ImpressionShare', 'Month', 'Quarter', 'Week', 'Year']

        elif report_type == 'CRITERIA_PERFORMANCE_REPORT':
            field_names = ['AdGroupId', 'AdGroupName', 'AdNetworkType', 'Age', 'AvgClickPosition',
                           'AvgCpc', 'AvgEffectiveBid', 'AvgImpressionPosition', 'AvgPageviews', 'AvgTrafficVolume',
                           'BounceRate', 'Bounces',
                           'CampaignId', 'CampaignName', 'CampaignUrlPath', 'CampaignType', 'CarrierType', 'Clicks',
                           'ClientLogin', 'ConversionRate', 'Conversions', 'Cost', 'CostPerConversion',
                           'Criterion', 'CriterionId', 'CriterionType',
                           'Ctr',
                           'Date', 'Device',
                           'ExternalNetworkName',
                           'Gender', 'GoalsRoi',
                           'Impressions', 'IncomeGrade',
                           'LocationOfPresenceId', 'LocationOfPresenceName',
                           'MatchType', 'MobilePlatform',
                           'Placement', 'Profit',
                           'Revenue', 'RlAdjustmentId',
                           'Sessions', 'Slot',
                           'TargetingCategory', 'TargetingLocationId', 'TargetingLocationName',
                           'WeightedCtr', 'WeightedImpressions']
        #             excluded: ['ClickType', 'Criteria', 'CriteriaId', 'CriteriaType', 'ImpressionShare',
        #                         'Month', 'Quarter', 'Week', 'Year']

        elif report_type == 'CUSTOM_REPORT':
            field_names = ['AdFormat', 'AdGroupId', 'AdGroupName', 'AdId', 'AdNetworkType', 'Age', 'AvgClickPosition',
                           'AvgCpc', 'AvgEffectiveBid', 'AvgImpressionPosition', 'AvgPageviews', 'AvgTrafficVolume',
                           'BounceRate', 'Bounces',
                           'CampaignId', 'CampaignName', 'CampaignUrlPath', 'CampaignType', 'CarrierType', 'Clicks',
                           'ClientLogin', 'ConversionRate', 'Conversions', 'Cost', 'CostPerConversion',
                           'Criterion', 'CriterionId', 'CriterionType',
                           'Ctr',
                           'Date', 'Device',
                           'ExternalNetworkName',
                           'Gender', 'GoalsRoi',
                           'Impressions', 'IncomeGrade',
                           'LocationOfPresenceId', 'LocationOfPresenceName',
                           'MatchType', 'MobilePlatform',
                           'Placement', 'Profit',
                           'Revenue', 'RlAdjustmentId',
                           'Sessions', 'Slot',
                           'TargetingCategory', 'TargetingLocationId', 'TargetingLocationName',
                           'WeightedCtr', 'WeightedImpressions']
        #             excluded: ['ClickType', 'Criteria', 'CriteriaId', 'CriteriaType', 'Month', 'Quarter', 'Week',
        #                           'Year']

        elif report_type == 'REACH_AND_FREQUENCY_PERFORMANCE_REPORT':
            field_names = ['AdGroupId', 'AdGroupName', 'AdId', 'Age', 'AvgCpc', 'AvgCpm', 'AvgEffectiveBid',
                           'AvgImpressionFrequency', 'AvgPageviews', 'AvgTrafficVolume',
                           'BounceRate', 'Bounces',
                           'CampaignId', 'CampaignName', 'CampaignUrlPath', 'CampaignType', 'Clicks',
                           'ClientLogin', 'ConversionRate', 'Conversions', 'Cost', 'CostPerConversion', 'Ctr',
                           'Date', 'Device',
                           'Gender', 'GoalsRoi',
                           'ImpressionReach', 'Impressions',
                           'Profit',
                           'Revenue',
                           'Sessions',
                           'TargetingLocationId', 'TargetingLocationName',
                           'WeightedCtr', 'WeightedImpressions']
        #             excluded: ['Month', 'Quarter', 'Week', 'Year']

        elif report_type == 'SEARCH_QUERY_PERFORMANCE_REPORT':
            field_names = ['AdGroupId', 'AdGroupName', 'AdId', 'AvgClickPosition', 'AvgCpc', 'AvgEffectiveBid',
                           'AvgImpressionPosition', 'AvgPageviews', 'AvgTrafficVolume',
                           'BounceRate', 'Bounces',
                           'CampaignId', 'CampaignName', 'CampaignUrlPath', 'CampaignType', 'Clicks', 'ClientLogin',
                           'ConversionRate', 'Conversions', 'Cost', 'CostPerConversion',
                           'Criterion', 'CriterionId', 'CriterionType', 'Ctr',
                           'Date',
                           'GoalsRoi',
                           'Impressions', 'IncomeGrade',
                           'MatchedKeyword', 'MatchType',
                           'Placement', 'Profit',
                           'Query',
                           'Revenue',
                           'TargetingCategory',
                           'WeightedCtr', 'WeightedImpressions']
        #             excluded: ['Criteria', 'CriteriaId', 'CriteriaType', 'Month', 'Quarter', 'Week', 'Year']

        return field_names

    def get_stat_report(self,
                        report_name,
                        report_type,
                        date_range_type,
                        include_vat,
                        format_='TSV',
                        goals=None,
                        attr_models=None,
                        limit=None,
                        offset=None,
                        order_by_fields=None,
                        order_by_sort_orders=None,
                        date_from=None,
                        date_to=None,
                        filter_fields=None,
                        filter_operators=None,
                        filter_values=None,
                        processing_mode='auto',
                        return_money_in_micros='false',
                        skip_report_header='false',
                        skip_column_header='false',
                        skip_report_summary='false'
                        ):
        """
        Статистический отчет
        https://yandex.ru/dev/direct/doc/reports/spec.html
        """
        service = 'reports'
        head = {"Authorization": 'Bearer' + ' ' + self.token,
                "Accept-Language": "ru",
                "Client-Login": self.login,
                #                 "Content-Type": "application/json; charset=utf-8",
                "processingMode": processing_mode,
                "returnMoneyInMicros": return_money_in_micros,
                "skipReportHeader": skip_report_header,
                "skipColumnHeader": skip_column_header,
                "skipReportSummary": skip_report_summary
                }

        field_names = self.get_field_names(report_type)

        body = {"params": {"FieldNames": field_names,
                           "ReportName": report_name,
                           "ReportType": report_type,
                           "DateRangeType": date_range_type,
                           "Format": format_,
                           "IncludeVAT": include_vat
                           }
                }

        body["params"].setdefault("SelectionCriteria", {})
        if goals is not None:
            body["params"].setdefault("Goals", goals)
        if attr_models is not None:
            body["params"].setdefault("AttributionModels", attr_models)
        if limit is not None:
            body["params"].setdefault("Page", {})
            body["params"]["Page"].setdefault("Limit", limit)
            if offset is not None:
                body["params"]["Page"].setdefault("Offset", offset)
        if order_by_fields is not None:
            body["params"].setdefault("OrderBy", [])
            body["params"]["OrderBy"] = [{"Field": field,
                                          "SortOrder": order} for field, order in zip(order_by_fields,
                                                                                      order_by_sort_orders)]
        if date_range_type == 'CUSTOM_DATE' and date_from is not None and date_to is not None:
            body["params"].setdefault("SelectionCriteria", {})
            body["params"]["SelectionCriteria"].setdefault("DateFrom", date_from)
            body["params"]["SelectionCriteria"].setdefault("DateTo", date_to)
        if filter_fields is not None and filter_operators is not None and filter_values is not None:
            body["params"].setdefault("SelectionCriteria", {})
            body["params"]["SelectionCriteria"].setdefault("Filter", [])
            body["params"]["SelectionCriteria"]["Filter"] = [{"Field": field,
                                                              "Operator": operator,
                                                              "Values": [i * 1e6 for i in values]}
                                                             for field, operator, values in zip(filter_fields,
                                                                                                filter_operators,
                                                                                                filter_values)]

        # Запуск цикла для выполнения запросов
        # Если получен HTTP-код 200, то выводится содержание отчета
        # Если получен HTTP-код 201 или 202, выполняются повторные запросы
        while True:
            try:
                req = requests.post(self.urls[2]+service, headers=head,
                                    data=json.dumps(body, indent=4).encode('utf8'))
                req.encoding = 'utf-8'  # Принудительная обработка ответа в кодировке "UTF-8"
                self.add_into_counter(response=req)
                if req.status_code == 400:
                    print("Параметры запроса указаны неверно или достигнут лимит отчетов в очереди")
                    print("RequestId: {}".format(req.headers.get("RequestId", False)))
                    print("JSON-код запроса: {}".format(self.u(body)))
                    print("JSON-код ответа сервера: \n{}".format(self.u(req.json())))
                    return req
                #                     break
                elif req.status_code == 200:
                    print("Отчет создан успешно")
                    print("RequestId: {}".format(req.headers.get("RequestId", False)))
                    # print("Содержание отчета: \n{}".format(self.u(req.text)))
                    sleep(0.6)
                    return req
                #                     break
                elif req.status_code == 201:
                    print("Отчет успешно поставлен в очередь в режиме офлайн")
                    retryIn = int(req.headers.get("retryIn", 60))
                    print("Повторная отправка запроса через {} секунд".format(retryIn))
                    print("RequestId: {}".format(req.headers.get("RequestId", False)))
                    sleep(retryIn)
                elif req.status_code == 202:
                    print("Отчет формируется в режиме офлайн")
                    retryIn = int(req.headers.get("retryIn", 60))
                    print("Повторная отправка запроса через {} секунд".format(retryIn))
                    print("RequestId:  {}".format(req.headers.get("RequestId", False)))
                    sleep(retryIn)
                elif req.status_code == 500:
                    print("При формировании отчета произошла ошибка. Пожалуйста, попробуйте повторить запрос позднее")
                    print("RequestId: {}".format(req.headers.get("RequestId", False)))
                    print("JSON-код ответа сервера: \n{}".format(self.u(req.json())))
                    return req
                #                     break
                elif req.status_code == 502:
                    print("Время формирования отчета превысило серверное ограничение.")
                    print("Пожалуйста, попробуйте изменить параметры запроса - уменьшить период и количество запрашиваемых данных.")
                    print("JSON-код запроса: {}".format(body))
                    print("RequestId: {}".format(req.headers.get("RequestId", False)))
                    print("JSON-код ответа сервера: \n{}".format(self.u(req.json())))
                    return req
                #                     break
                else:
                    print("Произошла непредвиденная ошибка")
                    print("RequestId:  {}".format(req.headers.get("RequestId", False)))
                    print("JSON-код запроса: {}".format(body))
                    print("JSON-код ответа сервера: \n{}".format(self.u(req.json())))
                    return None
            #                     break

            # Обработка ошибки, если не удалось соединиться с сервером API Директа
            except ConnectionError:
                # В данном случае мы рекомендуем повторить запрос позднее
                print("Произошла ошибка соединения с сервером API")
                # Принудительный выход из цикла
                return None
                # break

            # Если возникла какая-либо другая ошибка
            except:
                # В данном случае мы рекомендуем проанализировать действия приложения
                print("Произошла непредвиденная ошибка")
                # Принудительный выход из цикла
                return None
                # break

    @staticmethod
    def get_user_info(token):
        """
        Возвращает данные пользователя
        """
        url = 'https://login.yandex.ru/info?format=json'
        head = {'Authorization': f'OAuth {token}'}
        return requests.get(url, headers=head)


