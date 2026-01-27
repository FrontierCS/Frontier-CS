#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long Tid;
    if(!(cin>>Tid)) Tid=0;

    vector<string> lines;

    // 1) Normalize separator to 'S': map all allowed chars except a,b,c,S,A,B,C,D to S
    auto add_map = [&](char ch){
        string s; s.push_back(ch); s += "=S";
        lines.push_back(s);
    };
    for(char ch='0'; ch<='9'; ++ch){
        add_map(ch);
    }
    for(char ch='a'; ch<='z'; ++ch){
        if(ch=='a' || ch=='b' || ch=='c') continue;
        add_map(ch);
    }
    for(char ch='A'; ch<='Z'; ++ch){
        if(ch=='S' || ch=='A' || ch=='B' || ch=='C' || ch=='D') continue;
        add_map(ch);
    }

    // 2) Uppercase t: move S right while converting a,b,c to A,B,C
    lines.push_back("Sa=SA");
    lines.push_back("Sb=SB");
    lines.push_back("Sc=SC");
    lines.push_back("SA=AS");
    lines.push_back("SB=BS");
    lines.push_back("SC=CS");

    // 3) Append D before S when T ends at S
    lines.push_back("AS=ADS");
    lines.push_back("BS=BDS");
    lines.push_back("CS=CDS");

    // 4) Move S left across uppercase and D and lowercase to the very front
    lines.push_back("AS=SA");
    lines.push_back("BS=SB");
    lines.push_back("CS=SC");
    lines.push_back("DS=SD");
    lines.push_back("aS=Sa");
    lines.push_back("bS=Sb");
    lines.push_back("cS=Sc");

    // 5) Move T (A,B,C) and D leftwards across s (a,b,c): xU -> Ux
    lines.push_back("aA=Aa");
    lines.push_back("bA=Ab");
    lines.push_back("cA=Ac");
    lines.push_back("aB=Ba");
    lines.push_back("bB=Bb");
    lines.push_back("cB=Bc");
    lines.push_back("aC=Ca");
    lines.push_back("bC=Cb");
    lines.push_back("cC=Cc");
    lines.push_back("aD=Da");
    lines.push_back("bD=Db");
    lines.push_back("cD=Dc");

    // 6) Success detection: if T fully canceled, S adjacent to D
    lines.push_back("SD=(return)1");

    // 7) Cancellation when match: SAa -> S, SBb -> S, SCc -> S
    lines.push_back("SAa=S");
    lines.push_back("SBb=S");
    lines.push_back("SCc=S");

    // 8) Scanning step on mismatch: move U right by one across x (increase start index)
    // For A:
    lines.push_back("SAb=bSA");
    lines.push_back("SAc=cSA");
    // For B:
    lines.push_back("SBa=aSB");
    lines.push_back("SBc=cSB");
    // For C:
    lines.push_back("SCa=aSC");
    lines.push_back("SCb=bSC");
    // Move D as well (carry along)
    lines.push_back("SDa=aSD");
    lines.push_back("SDb=bSD");
    lines.push_back("SDc=cSD");

    // 9) Failure detection at end (no x to move across, no cancellation possible)
    lines.push_back("SA=(return)0");
    lines.push_back("SB=(return)0");
    lines.push_back("SC=(return)0");

    // Output
    for(auto &s: lines) cout << s << "\n";
    return 0;
}