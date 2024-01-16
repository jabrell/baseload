*$if not set data $set data "../text.gdx"

Set
    i   generation technologies
*    /i1/
    s   storage technologies
*    /s1/
    t   time periods
*    /t1*t10000/
;

Parameter
    dem(t)              demand in time period t [MWh]
    alpha(i,t)          share of annual generation of technology i eneding up in period t
    agen(i)             annual generation of technology i
    max_sto(s)          size storage [MWh]
    curtailment(i,t)    curtailment of technology i in period t [MW]
    lostload            total lost load [MWh]
    stats[*]            solution statistics
    cost_curtailment(i) for adding curtailment amount ot objectiv
;

$gdxin %data%
$load i s t
$loaddc dem alpha agen max_sto cost_curtailment
$gdxin


Variable
    COST            objective value
;

Positive Variable
    GEN(i,t)        generation of technology i in period t [MW]
    STO(s,t)        storage level in period t [MWh]
    INJ(s,t)        storage injection in period t [MW]
    REL(s,t)        storage relase in period t [MW]
    ENS(t)          energy not served in period t
;

Equations
    obj             objective function: sum of lost load [MWh]
    mkt(t)          energy balance in period t [MW]
    res_maxGEN(i,t) maximum generation technology i period t [MW]
    res_maxSTO(s,t) maximum storage content storage s in period t [MWh]
    lom_STO(s,t)    stoarge accounting [MWh]
;


obj..
    COST                    =E= sum(t, ENS(t)
                                + sum(i, cost_curtailment(i)*(alpha(i,t)*agen(i) - GEN(i,t)))
                                )
;

mkt(t)..
    sum(i, GEN(i,t)) + sum(s, STO(s,t)) + ENS(t)
                            =E= dem(t)
;

res_maxGEN(i,t)..
    alpha(i,t)*agen(i)      =G= GEN(i,t)
;

res_maxSTO(s,t)..
    max_STO(s)              =G= STO(s,t)
;

lom_STO(s,t)..
    STO(s,t--1) + INJ(s,t) - REL(s,t)
                            =E= STO(s,t) 
;

model baseload /obj, mkt, res_maxGEN, res_maxSTO, lom_STO/;

solve baseload using LP minimzing COST;

curtailment(i,t) = alpha(i,t)*agen(i) - GEN.L(i,t);
lostload = COST.L;
stats["modelstat"] = baseload.modelstat;
stats["solvestat"] = baseload.solvestat;