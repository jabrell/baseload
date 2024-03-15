$onText
This model version minimizes the amount of storage necessary
to fullfill total demand. Dispatchable generation is assumed
to be zero and total generation of renewbales and baseload
together with the production profile is exogenously provided.
$offText

*$if not set data $set data "./test.gdx"

Set
    i     generation technologies
    r(i)  renewable technologies
    s     storage technologies
    t     time periods
;
alias(r,rr);

Parameter
    dem(t)              demand in time period t [MWh]
    alpha(i,t)          share of annual generation of technology i eneding up in period t
    agen(i)             annual generation of technology i
    agen_re             possible annual generation renewables
    sh_res(r)           share of renewable technology r in annual output of renewables
    curtailment(i,t)    curtailment of technology i in period t [MW]
    lostload            total lost load [MWh]
    stats[*]            solution statistics
    cost_curtailment(i) for adding curtailment amount ot objectiv
    optimize_res_share  if one then the RES technology share is optimized
;

$gdxin %data%
$load i s t r
$loaddc dem alpha agen cost_curtailment agen_re sh_res optimize_res_share

Variable
    COST            objective value
;

Positive Variable
    GEN(i,t)        generation of technology i in period t [MW]
    STO(s,t)        storage level in period t [MWh]
    INJ(s,t)        storage injection in period t [MW]
    REL(s,t)        storage relase in period t [MW]s
    MAX_STO         maximum amout of storage possible
    ENS(t)          energy not served (not used in this model)
    SHARE_RE(r)     share of renewable technology r in total renewable generation
;

Equations
    obj             objective function: sum of lost load [MWh]
    mkt(t)          energy balance in period t [MW]
    res_maxGEN(i,t) maximum generation technology i period t [MW]
    res_maxSTO(s,t) maximum storage content storage s in period t [MWh]
    lom_STO(s,t)    stoarge accounting [MWh]
    res_re_share    RE shares need to sum to one
;

obj..
    COST                    =E= (MAX_STO
                                    + sum((t,i)$(not r(i)), cost_curtailment(i)*(alpha(i,t)*agen(i) - GEN(i,t)))
                                    + sum((t,r), cost_curtailment(r)*(alpha(r,t)*agen_re*SHARE_RE(r) - GEN(r,t)))
                                )
;

mkt(t)..
    sum(i, GEN(i,t)) + sum(s, REL(s,t) - INJ(s,t))
                            =E= dem(t)
;

res_maxGEN(i,t)..
    (alpha(i,t)*agen(i))$(not r(i))
    + sum(r$sameas(r,i), alpha(r,t)*agen_re*SHARE_RE(r))
                            =G= GEN(i,t)
;

res_maxSTO(s,t)..
    MAX_STO                 =G= STO(s,t)
;

lom_STO(s,t)..
    STO(s,t--1) + INJ(s,t) - REL(s,t)
                            =E= STO(s,t) 
;

res_re_share..
    sum(r, SHARE_RE(r))     =E= 1
;

display sh_res;

* fix the RE share if not optimized
SHARE_RE.L(r) = sh_res(r);
SHARE_RE.UP(r) = 1;
SHARE_RE.FX(r)$(not optimize_res_share) = sh_res(r);
* in the case of optimizing the share we need to marginally increase annual RE generation
* to avoid unscaled infeasibilites. To not distort the comparison, we do this for both
* cases
agen_re = agen_re*1.000000001;
agen(i) = agen(i)*1.000000001;

model baseload /obj, mkt, res_maxGEN, res_maxSTO, lom_STO, res_re_share/;

* the option file
baseload.optfile = 1 ;
$onecho > cplex.opt
scaind=1
names=no
$offecho

solve baseload using LP minimzing COST;

curtailment(i,t) = alpha(i,t)*agen(i) - GEN.L(i,t);
curtailment(r,t) = alpha(r,t)*agen_re*SHARE_RE.L(r) - GEN.L(r,t);
lostload = COST.L;
stats["modelstat"] = baseload.modelstat;
stats["solvestat"] = baseload.solvestat;
