#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long Tid;
    if (!(cin >> Tid)) return 0;

    vector<string> out;

    // Insert initial head I before separator S and end marker Z after it
    out.push_back("S=ISZ");

    // Expand t into pairs (char + bit0) using Z as a moving cursor
    out.push_back("Za=a0Z");
    out.push_back("Zb=b0Z");
    out.push_back("Zc=c0Z");

    // Bubble I to the beginning of the whole string
    out.push_back("aI=Ia");
    out.push_back("bI=Ib");
    out.push_back("cI=Ic");

    // Consume the first character with I and insert sentinel X
    out.push_back("Ia=XAP");
    out.push_back("Ib=XBQ");
    out.push_back("Ic=XCR");

    // DP update rules (Shift-And) on t pairs
    struct Inp {
        char ch;
        char up;   // marker carry=1
        char low;  // marker carry=0
    };
    vector<Inp> inputs = {
        {'a','P','p'},
        {'b','Q','q'},
        {'c','R','r'}
    };
    vector<char> tchars = {'a','b','c'};
    vector<char> bits = {'0','1'};

    for (auto in : inputs) {
        for (int carry = 1; carry >= 0; --carry) {
            char curM = carry ? in.up : in.low;
            for (char tc : tchars) {
                for (char ob : bits) {
                    char newb = (carry && tc == in.ch) ? '1' : '0';
                    char nextM = (ob == '1') ? in.up : in.low;
                    string s1;
                    s1 += curM; s1 += tc; s1 += ob;
                    string s2;
                    s2 += tc; s2 += newb; s2 += nextM;
                    out.push_back(s1 + "=" + s2);
                }
            }
        }
    }

    // If last bit is 1 right before Z, return 1
    out.push_back("1PZ=(return)1");
    out.push_back("1pZ=(return)1");
    out.push_back("1QZ=(return)1");
    out.push_back("1qZ=(return)1");
    out.push_back("1RZ=(return)1");
    out.push_back("1rZ=(return)1");

    // Finish update: turn any marker at end into K (returning marker) before Z
    out.push_back("PZ=KZ");
    out.push_back("pZ=KZ");
    out.push_back("QZ=KZ");
    out.push_back("qZ=KZ");
    out.push_back("RZ=KZ");
    out.push_back("rZ=KZ");

    // Move K left across lowercase, digits, and separator
    out.push_back("aK=Ka");
    out.push_back("bK=Kb");
    out.push_back("cK=Kc");
    out.push_back("0K=K0");
    out.push_back("1K=K1");
    out.push_back("SK=KS");

    // Convert K into head H when it reaches the processed boundary
    out.push_back("XK=XH");
    out.push_back("AK=AH");
    out.push_back("BK=BH");
    out.push_back("CK=CH");

    // Consume next s character with H (mark processed as uppercase, spawn marker)
    out.push_back("Ha=AP");
    out.push_back("Hb=BQ");
    out.push_back("Hc=CR");

    // Move marker (P/Q/R) right across remaining unprocessed s and across S into t
    out.push_back("Pa=aP");
    out.push_back("Pb=bP");
    out.push_back("Pc=cP");
    out.push_back("PS=SP");

    out.push_back("Qa=aQ");
    out.push_back("Qb=bQ");
    out.push_back("Qc=cQ");
    out.push_back("QS=SQ");

    out.push_back("Ra=aR");
    out.push_back("Rb=bR");
    out.push_back("Rc=cR");
    out.push_back("RS=SR");

    // End: if H reaches S, no match found
    out.push_back("HS=(return)0");

    for (auto &line : out) cout << line << "\n";
    return 0;
}