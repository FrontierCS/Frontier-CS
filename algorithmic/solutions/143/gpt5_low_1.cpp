#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cout.setf(std::ios::fixed);
    cout<<setprecision(6);

    long long rate_budget_remaining = 3000000;

    int G;
    if(!(cin >> G)) return 0;
    if(G == -1) return 0;

    string tok;
    while (cin >> tok) {
        if(tok == "-1") return 0;

        if(tok == "STATE") {
            int h,r,a,b,P,k;
            cin >> h >> r >> a >> b >> P >> k;

            string s;
            cin >> s; // "ALICE"
            if(s == "-1") return 0;
            int as1,av1,as2,av2;
            cin >> as1 >> av1 >> as2 >> av2;

            cin >> s; // "BOARD"
            if(s == "-1") return 0;
            vector<pair<int,int>> board;
            for(int i=0;i<k;i++){
                int cs, cv;
                cin >> cs >> cv;
                board.emplace_back(cs,cv);
            }

            // Decide RATE t based on round
            int t = 0;
            if(r==1) t = 30;
            else if(r==2) t = 60;
            else if(r==3) t = 90;
            else t = 120;

            if(rate_budget_remaining <= 0) t = 0;
            else if(rate_budget_remaining < t) t = (int)rate_budget_remaining;

            double w=0.5, d=0.0;
            if(t > 0) {
                cout << "RATE " << t << endl;
                cout.flush();
                string rtok;
                if(!(cin >> rtok)) return 0;
                if(rtok == "-1") return 0;
                if(rtok != "RATES") {
                    // Unexpected, try to handle but safest exit
                    return 0;
                }
                cin >> w >> d;
                rate_budget_remaining -= t;
            }

            // Compute decision
            double val = 2.0*w + d - 1.0;
            int x = 0;
            string action;

            if(a <= 0) {
                action = "CHECK";
            } else if(val > 0.0) {
                // Value bet small to encourage calls
                x = min(5, a);
                if(x < 1) action = "CHECK";
                else {
                    action = "RAISE " + to_string(x);
                }
            } else {
                // Consider bluff with x=1 if it makes Bob fold in our model
                double A = 1.0 - w - 0.5*d;
                double B = 1.0 - 2.0*w - d;
                if(B >= 0.0 && (A * P + B * 1.0) <= 0.0 && a >= 1) {
                    x = 1;
                    action = "RAISE 1";
                } else {
                    action = "CHECK";
                }
            }

            cout << "ACTION " << action << endl;
            cout.flush();
        } else if(tok == "OPP") {
            string what; cin >> what;
            if(what == "-1") return 0;
            if(what == "CALL") {
                int x; cin >> x;
            }
            // OPP FOLD or OPP CHECK have no extra tokens except CALL x handled above
        } else if(tok == "RESULT") {
            int delta; cin >> delta;
        } else if(tok == "RATES") {
            // In case judge sends RATES unexpectedly (should only after our RATE)
            double w, d; cin >> w >> d;
        } else if(tok == "SCORE") {
            double W; cin >> W;
            break;
        } else if(tok == "ALICE" || tok == "BOARD") {
            // Shouldn't occur standalone, but consume if necessary
            // Try to skip reasonable tokens; however protocol ensures these follow STATE.
        } else {
            // Unknown token; check for immediate termination
            if(tok == "-1") return 0;
            // Otherwise ignore or exit
        }
    }

    return 0;
}