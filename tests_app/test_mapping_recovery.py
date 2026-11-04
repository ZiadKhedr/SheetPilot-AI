import json
import pytest
from sheetpilot.mapping import meta_mapping, validate_fields
from sheetpilot.models import SemanticPlan
from sheetpilot.provider import MetaError
from sheetpilot.store import Problem
from .test_advanced_mapping import retail_store, proposal_for


def with_currency_column(store,workspace):
    table=next(t for t in store.list(workspace,'table') if t['sheet']=='Sales')
    # Use a real existing column index in a contract proposal; currency evidence
    # validation is independent of semantic human review, never auto-confirmed.
    return table


def test_redundant_header_currency_with_currency_column_is_only_a_proposal(tmp_path):
    store,w,_,_=retail_store(tmp_path);table=with_currency_column(store,w)
    class Provider:
        model='test-contract';calls=0
        def structured(self,messages,schema):
            self.calls+=1;p=proposal_for(table)
            p['fields']=[f for f in p['fields'] if f['column_index']!=7]+[dict(column_index=7,field='currency',confidence=.8,evidence='Contract currency column')]
            return schema.model_validate({'tables':[p],'summary':'Proposal only'})
    provider=Provider();meta_mapping(store,w,provider,[table['id']])
    result=store.get(w,'table',table['id'])
    assert result['fields']['7']=='currency' and result['constants']=={}
    assert result['status']=='suggested' and provider.calls==1


def test_retry_receives_exact_duplicate_field_diagnostic_and_rejected_mapping(tmp_path):
    store,w,_,_=retail_store(tmp_path);table=with_currency_column(store,w)
    class Provider:
        model='test-contract';calls=0
        def structured(self,messages,schema):
            self.calls+=1;p=proposal_for(table)
            if self.calls==1:
                p['fields'][4]['field']='list_unit_price'
            else:
                assert 'list_unit_price in columns 4, 5' in messages[-1]['content']
                previous=json.loads(messages[-2]['content'])
                assert previous['tables'][0]['table_id']==table['id']
            return schema.model_validate({'tables':[p],'summary':'Corrected proposal'})
    provider=Provider();meta_mapping(store,w,provider,[table['id']]);assert provider.calls==2


def test_invalid_columns_and_currency_still_fail_atomically(tmp_path):
    store,w,_,_=retail_store(tmp_path);table=with_currency_column(store,w)
    class Provider:
        model='test-contract'
        def structured(self,messages,schema):
            p=proposal_for(table);p['fields'][0]['column_index']=99
            return schema.model_validate({'tables':[p],'summary':'Invalid'})
    with pytest.raises(MetaError,match='outside this table: 99'):meta_mapping(store,w,Provider(),[table['id']])
    assert all(t['revision']==0 for t in store.list(w,'table'))
    class BadCurrency(Provider):
        def structured(self,messages,schema):
            p=proposal_for(table);p['currency']='USD'
            return schema.model_validate({'tables':[p],'summary':'Invalid'})
    with pytest.raises(MetaError,match='currency'):meta_mapping(store,w,BadCurrency(),[table['id']])
    assert all(t['revision']==0 for t in store.list(w,'table'))


def test_manual_review_still_rejects_two_currency_sources_and_repeated_meanings():
    table={'columns':[{'index':1},{'index':2}]}
    with pytest.raises(Problem,match='not both'):validate_fields(table,{'1':'currency'},'unknown',False,{'currency':'EGP'})
    with pytest.raises(Problem,match='Repeated meanings'):validate_fields(table,{'1':'product_id','2':'product_id'},'unknown',False)
