import requests
from abridge_bot.settings import PROXY_API_KEY



class ProxyConnector(object):
    url = 'https://proxy6.net/api/{api_key}/{method}/?{params}'
    
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        resp = self.get_status()
        assert resp['status'] == 'yes', 'Connection Error'
        
    
    def __get_url(self, **kwargs) -> dict:
        method = kwargs.pop('method', None)
        params = '&'.join([f'{k}={v}' for k, v in kwargs.items() if v != ''])
        
        if method:
            if len(params) > 0:
                url = self.url.format(api_key=self.api_key, method=method, params=params[:-1])
            else:
                url = self.url.format(api_key=self.api_key, method=method, params='')[:-2]
        else:
            url = self.url.format(api_key=self.api_key, method='', params='')[:-3]
            
        return url
    
    
    def __return_data(self, url: str) -> dict:
        resp = requests.get(url)
        return resp.json()
    
    
    def get_status(self) -> dict:
        url = self.__get_url()
        return self.__return_data(url)
    
    
    def get_price(self, period: int, version: int, count: int) -> dict:
        url = self.__get_url(
            method='getprice', 
            count=count, period=period, version=version
        )
        return self.__return_data(url)
    
    
    def get_count(self, country: str = '', version: int = '') -> dict:
        url = self.__get_url(
            method='getcount', 
            country=country, version=version
        )
        return self.__return_data(url)
    
    
    def get_country(self, version: int) -> dict:
        url = self.__get_url(
            method='getcountry', 
            version=version
        )
        return self.__return_data(url)
    
    
    def get_proxy(self, state: str = '', descr: str = '') -> dict:
        url = self.__get_url(
            method='getproxy', 
            state=state, descr=descr
        )
        return self.__return_data(url)
    
    
    def set_type(self, ids: str, type: str = 'socks') -> dict:
        url = self.__get_url(
            method='settype', 
            ids=ids, type=type
        )
        return self.__return_data(url)
    
    
    def set_descr(self, ids: str, new: str = '', descr: str = '') -> dict:
        url = self.__get_url(
            method='setdescr', 
            new=new, ids=ids, descr=descr
        )
        return self.__return_data(url)
    

    def buy(self, count: int, period: int, country: str, type: str = 'socks', auto_prolong: bool = False, descr: str = '') -> dict:
        url = self.__get_url(
            method='buy', 
            count=count, period=period, 
            country=country, type=type, auto_prolong=auto_prolong, 
            descr=descr
        )
        return self.__return_data(url)
    
    def prolong(self, period: int, ids: str) -> dict:
        url = self.__get_url(
            method='prolong', 
            ids=ids, period=period
        )
        return self.__return_data(url)
    
    
    def deleted(self, ids: str, descr: str = '') -> dict:
        url = self.__get_url(
            method='deleted', 
            ids=ids, descr=descr
        )
        return self.__return_data(url)
    
    
    def check(self, ids: str) -> dict:
        url = self.__get_url(
            method='check', 
            ids=ids
        )
        return self.__return_data(url)

        
        
proxy_connector = ProxyConnector(PROXY_API_KEY)