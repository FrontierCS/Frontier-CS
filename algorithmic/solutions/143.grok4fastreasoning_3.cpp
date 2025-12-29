#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);
    int G;
    cin >> G;
    for(int hand_num = 1; hand_num <= G; hand_num++) {
        bool hand_done = false;
        while (!hand_done) {
            string cmd;
            cin >> cmd;
            if (cmd == "-1") return 0;
            int h, rnd, a, b, P, k;
            cin >> h >> rnd >> a >> b >> P >> k;
            string al;
            cin >> al;
            int as1, av1, as2, av2;
            cin >> as1 >> av1 >> as2 >> av2;
            string bd;
            cin >> bd;
            vector<pair<int, int>> brd(k);
            for (int i = 0; i < k; i++) {
                int s, v;
                cin >> s >> v;
                brd[i] = {s, v};
            }
            int t_query = 0;
            if (rnd == 1) t_query = 20;
            else if (rnd == 2) t_query = 40;
            else if (rnd == 3) t_query = 80;
            else if (rnd == 4) t_query = 160;
            double winp = 0.5, tiep = 0.0;
            if (t_query > 0) {
                cout << "RATE " << t_query << endl;
                string rcmd;
                cin >> rcmd;
                if (rcmd == "-1") return 0;
                if (rcmd == "RATES") {
                    cin >> winp >> tiep;
                }
            }
            double equity = winp + 0.5 * tiep;
            double check_ev = a + winp * P + tiep * (P / 2.0) - 100.0;
            double best_raise_ev = check_ev;
            int best_x = 0;
            for (int xx = 1; xx <= a; xx++) {
                double px = P + 2.0 * xx;
                double be_my = (P + (double)xx) / px;
                double this_ev;
                if (equity >= be_my) {
                    this_ev = a + P + (double)xx - 100.0;
                } else {
                    this_ev = a - (double)xx + equity * px - 100.0;
                }
                if (this_ev > best_raise_ev) {
                    best_raise_ev = this_ev;
                    best_x = xx;
                }
            }
            string act;
            if (best_x > 0 && best_raise_ev > check_ev + 1e-9) {  // to avoid float equal
                act = "RAISE " + to_string(best_x);
            } else {
                act = "CHECK";
            }
            cout << "ACTION " << act << endl;
            string resp1;
            cin >> resp1;
            if (resp1 == "-1") return 0;
            if (act.find("CHECK") != string::npos) {
                string resp2;
                cin >> resp2;
                if (resp2 == "-1") return 0;
                if (rnd == 4) {
                    string res_cmd;
                    cin >> res_cmd;
                    if (res_cmd == "-1") return 0;
                    int delta;
                    cin >> delta;
                    hand_done = true;
                }
            } else {
                string opp;
                cin >> opp;
                if (opp == "-1") return 0;
                string opp_act;
                cin >> opp_act;
                if (opp_act == "-1") return 0;
                if (opp_act == "FOLD") {
                    string res_cmd;
                    cin >> res_cmd;
                    if (res_cmd == "-1") return 0;
                    int delta;
                    cin >> delta;
                    hand_done = true;
                } else {
                    int called_x;
                    cin >> called_x;
                    if (rnd == 4) {
                        string res_cmd;
                        cin >> res_cmd;
                        if (res_cmd == "-1") return 0;
                        int delta;
                        cin >> delta;
                        hand_done = true;
                    }
                }
            }
        }
    }
    string score_cmd;
    double score_val;
    cin >> score_cmd >> score_val;
    return 0;
}