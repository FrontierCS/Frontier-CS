#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long Tid;
    if (!(cin >> Tid)) return 0;

    vector<string> p = {
        "a=A0",
        "b=B0",
        "c=C0",
        "S=LD",
        "0L=L0",
        "AL=LA",
        "BL=LB",
        "CL=LC",
        "DA1=(return)1",
        "DB1=(return)1",
        "DC1=(return)1",
        "A0D=EQ",
        "B0D=ER",
        "C0D=EU",

        "QA0=A0Q",
        "QA1=A1Q",
        "QB0=B0Q",
        "QB1=B1Q",
        "QC0=C0Q",
        "QC1=C1Q",

        "RA0=A0R",
        "RA1=A1R",
        "RB0=B0R",
        "RB1=B1R",
        "RC0=C0R",
        "RC1=C1R",

        "UA0=A0U",
        "UA1=A1U",
        "UB0=B0U",
        "UB1=B1U",
        "UC0=C0U",
        "UC1=C1U",

        "Q=q",
        "R=s",
        "U=u",

        "A0p=pA0",
        "A1p=qA0",
        "B0p=pB0",
        "B1p=qB0",
        "C0p=pC0",
        "C1p=qC0",

        "A0q=pA1",
        "A1q=qA1",
        "B0q=pB0",
        "B1q=qB0",
        "C0q=pC0",
        "C1q=qC0",

        "A0r=rA0",
        "A1r=sA0",
        "B0r=rB0",
        "B1r=sB0",
        "C0r=rC0",
        "C1r=sC0",

        "A0s=rA0",
        "A1s=sA0",
        "B0s=rB1",
        "B1s=sB1",
        "C0s=rC0",
        "C1s=sC0",

        "A0t=tA0",
        "A1t=uA0",
        "B0t=tB0",
        "B1t=uB0",
        "C0t=tC0",
        "C1t=uC0",

        "A0u=tA0",
        "A1u=uA0",
        "B0u=tB0",
        "B1u=uB0",
        "C0u=tC1",
        "C1u=uC1",

        "Ep=E",
        "Eq=E",
        "Er=E",
        "Es=E",
        "Et=E",
        "Eu=E",

        "EA=DA",
        "EB=DB",
        "EC=DC",

        "LD=(return)0"
    };

    for (auto &line : p) cout << line << "\n";
    return 0;
}