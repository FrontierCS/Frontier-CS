#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);
    int G;
    cin >> G;
    if (G == -1) return 0;
    for (int hand = 1; hand <= G; hand++) {
        bool hand_ended = false;
        while (!hand_ended) {
            string token;
            cin >> token;
            if (token == "-1") return 0;
            if (token != "STATE") continue; // safety
            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;
            string alice_tag;
            cin >> alice_tag;
            if (alice_tag == "-1") return 0;
            int s1, v1, s2, v2;
            cin >> s1 >> v1 >> s2 >> v2;
            string board_tag;
            cin >> board_tag;
            if (board_tag == "-1") return 0;
            vector<pair<int, int>> board(k);
            for (int i = 0; i < k; i++) {
                int s, v;
                cin >> s >> v;
            }
            // RATE query
            int t = 50;
            cout << "RATE " << t << endl;
            string rates_tag;
            cin >> rates_tag;
            if (rates_tag == "-1") return 0;
            if (rates_tag != "RATES") continue; // safety
            double w, d;
            cin >> w >> d;
            double e = w + 0.5 * d;
            // Decide action
            string act_type = "CHECK";
            int x = 0;
            double target = 0.0;
            if (e > 0.75) {
                target = 1.5 * P;
            } else if (e > 0.6) {
                target = 0.5 * P;
            } else if (e > 0.55 && r >= 2) {
                target = 0.25 * P + 2;
            }
            if (target >= 1.0) {
                x = (int)round(target);
                x = max(1, min(x, a));
                act_type = "RAISE";
            }
            // Output action
            cout << "ACTION " << act_type;
            if (act_type == "RAISE") {
                cout << " " << x;
            }
            cout << endl;
            // Read response
            string resp;
            cin >> resp;
            if (resp == "-1") return 0;
            if (act_type == "CHECK") {
                string opp_act;
                cin >> opp_act;
                if (opp_act == "-1") return 0;
                if (r == 4) {
                    string res_tag;
                    cin >> res_tag;
                    if (res_tag == "-1") return 0;
                    int delta;
                    cin >> delta;
                    hand_ended = true;
                }
            } else { // RAISE
                string opp_act;
                cin >> opp_act;
                if (opp_act == "-1") return 0;
                if (opp_act == "FOLD") {
                    string res_tag;
                    cin >> res_tag;
                    if (res_tag == "-1") return 0;
                    int delta;
                    cin >> delta;
                    hand_ended = true;
                } else { // CALL
                    int called_x;
                    cin >> called_x;
                    if (r == 4) {
                        string res_tag;
                        cin >> res_tag;
                        if (res_tag == "-1") return 0;
                        int delta;
                        cin >> delta;
                        hand_ended = true;
                    }
                }
            }
        }
    }
    return 0;
}