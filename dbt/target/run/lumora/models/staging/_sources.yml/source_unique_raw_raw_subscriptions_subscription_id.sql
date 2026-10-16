
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    subscription_id as unique_field,
    count(*) as n_records

from LUMORA.RAW.raw_subscriptions
where subscription_id is not null
group by subscription_id
having count(*) > 1



  
  
      
    ) dbt_internal_test