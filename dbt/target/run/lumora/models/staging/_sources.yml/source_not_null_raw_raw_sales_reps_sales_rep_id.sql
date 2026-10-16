
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select sales_rep_id
from LUMORA.RAW.raw_sales_reps
where sales_rep_id is null



  
  
      
    ) dbt_internal_test