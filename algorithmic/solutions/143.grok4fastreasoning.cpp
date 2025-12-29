#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int G;
    cin >> G;
    long long remaining_budget = 3000000LL;
    string token;
    while (cin >> token) {
        if (token == "-1") return 0;
        if (token == "SCORE") {
            double w;
            cin >> w;
            return 0;
        }
        if (token != "STATE") continue;
        int h, r, a, b, P, k;
        cin >> h >> r >> a >> b >> P >> k;
        string alice_str;
        cin >> alice_str;
        if (alice_str == "-1") return 0;
        if (alice_str != "ALICE") continue;
        int s1, v1, s2, v2;
        cin >> s1 >> v1 >> s2 >> v2;
        string board_str;
        cin >> board_str;
        if (board_str == "-1") return 0;
        if (board_str != "BOARD") continue;
        vector<pair<int, int>> community(k);
        for (int i = 0; i < k; i++) {
            int cs, cv;
            cin >> cs >> cv;
            community[i] = {cs, cv};
        }
        // Decide t
        int t = 0;
        if (r == 1) t = 20;
        else if (r == 2) t = 60;
        else if (r == 3) t = 80;
        else t = 100;
        double equity = 0.5;
        if (remaining_budget >= t && t > 0) {
            cout << "RATE " << t << endl;
            cout.flush();
            remaining_budget -= t;
            string rates_str;
            cin >> rates_str;
            if (rates_str == "-1") return 0;
            if (rates_str == "RATES") {
                double w, d;
                cin >> w >> d;
                equity = w + 0.5 * d;
            }
        }
        // Decide action
        int x = 0;
        if (r == 4) {
            // River
            if (equity > 0.5) {
                x = max(1, P / 2);
                x = min(x, a);
            } else if (equity < 0.4) {
                x = max(1, P / 2);
                x = min(x, a);
            }
        } else {
            // Other rounds
            double v_thresh = 0.6 - 0.025 * (r - 1);
            double b_thresh = 0.4 + 0.025 * (r - 1);
            if (equity > v_thresh) {
                x = max(1, (int)(P * (0.25 + 0.1 * (r - 1))));
                x = min(x, a / (5 - r));
            } else if (equity < b_thresh) {
                x = max(1, (int)(P * (0.5 + 0.15 * (r - 1))));
                x = min(x, a / (5 - r));
            }
        }
        if (x > a || x < 1) x = 0;
        string action_str = (x == 0 ? "CHECK" : "RAISE " + to_string(x));
        bool is_check = (x == 0);
        bool is_raise = (x > 0);
        cout << "ACTION " << action_str << endl;
        cout.flush();
        // Handle response
        string first_resp;
        cin >> first_resp;
        if (first_resp == "-1") return 0;
        if (!is_check && !is_raise) {
            // fold, expect RESULT
            if (first_resp != "RESULT") continue;
            int delta;
            cin >> delta;
        } else {
            if (first_resp != "OPP") continue;
            string opp_act;
            cin >> opp_act;
            if (opp_act == "-1") return 0;
            if (is_check) {
                if (opp_act != "CHECK") continue;
                if (r == 4) {
                    string res_str;
                    cin >> res_str;
                    if (res_str == "-1") return 0;
                    if (res_str != "RESULT") continue;
                    int delta;
                    cin >> delta;
                }
            } else if (is_raise) {
                if (opp_act == "FOLD") {
                    string res_str;
                    cin >> res_str;
                    if (res_str == "-1") return 0;
                    if (res_str != "RESULT") continue;
                    int delta;
                    cin >> delta;
                } else if (opp_act == "CALL") {
                    int call_x;
                    cin >> call_x;
                    if (r == 4) {
                        string res_str;
                        cin >> res_str;
                        if (res_str == "-1") return 0;
                        if (res_str != "RESULT") continue;
                        int delta;
                        cin >> delta;
                    }
                }
            }
        }
    }
    return 0;
}