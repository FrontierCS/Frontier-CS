#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long Tid;
    if (!(cin >> Tid)) return 0;

    vector<string> prog = {
        "S=XY",
        "Ya=aY",
        "Yb=bY",
        "Yc=cY",
        "XA=(return)1",
        "XB=(return)1",
        "XC=(return)1",

        "paA=pDA",
        "paB=pDB",
        "paC=pDC",
        "paY=pDY",
        "pAA=pDA",
        "pAB=pDB",
        "pAC=pDC",
        "pAY=pDY",

        "qbA=qEA",
        "qbB=qEB",
        "qbC=qEC",
        "qbY=qEY",
        "qBA=qEA",
        "qBB=qEB",
        "qBC=qEC",
        "qBY=qEY",

        "rcA=rFA",
        "rcB=rFB",
        "rcC=rFC",
        "rcY=rFY",
        "rCA=rFA",
        "rCB=rFB",
        "rCC=rFC",
        "rCY=rFY",

        "pa=ap",
        "pb=bp",
        "pc=cp",
        "pA=Ap",
        "pB=Bp",
        "pC=Cp",
        "pD=Dp",
        "pE=Ep",
        "pF=Fp",

        "qa=aq",
        "qb=bq",
        "qc=cq",
        "qA=Aq",
        "qB=Bq",
        "qC=Cq",
        "qD=Dq",
        "qE=Eq",
        "qF=Fq",

        "ra=ar",
        "rb=br",
        "rc=cr",
        "rA=Ar",
        "rB=Br",
        "rC=Cr",
        "rD=Dr",
        "rE=Er",
        "rF=Fr",

        "pY=UY",
        "qY=UY",
        "rY=UY",

        "aU=Ua",
        "bU=Ub",
        "cU=Uc",
        "AU=Ua",
        "BU=Ub",
        "CU=Uc",
        "DU=UA",
        "EU=UB",
        "FU=UC",
        "XU=X",

        "aX=Xp",
        "bX=Xq",
        "cX=Xr",

        "=(return)0"
    };

    for (auto &line : prog) cout << line << "\n";
    return 0;
}