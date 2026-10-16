
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    sales_rep_id as unique_field,
    count(*) as n_records

from LUMORA.RAW.raw_sales_reps
where sales_rep_id is not null
group by sales_rep_id
having count(*) > 1



  
  
      
    ) dbt_internal_test