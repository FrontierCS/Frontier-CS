#include <bits/stdc++.h>
using namespace std;

static const long long RATE_BUDGET_TOTAL = 3000000;

struct State {
    int h, r, a, b, P, k;
    int as, av, bs, bv; // our two cards (suit,value)
    vector<pair<int,int>> board;
};

long long rate_budget_left = RATE_BUDGET_TOTAL;

pair<double,double> request_rates(int t) {
    if (t <= 0) t = 1;
    if (rate_budget_left <= 0) {
        return {0.5, 0.0};
    }
    if ((long long)t > rate_budget_left) t = (int)rate_budget_left;
    rate_budget_left -= t;
    cout << "RATE " << t << endl;
    cout.flush();

    string tok;
    if (!(cin >> tok)) exit(0);
    if (tok == "-1") exit(0);
    // Expect "RATES"
    while (tok != "RATES") {
        if (tok == "-1") exit(0);
        // Drain unexpected tokens just in case
        if (!(cin >> tok)) exit(0);
    }
    double w, d;
    if (!(cin >> w >> d)) exit(0);
    return {w, d};
}

string decide_action(const State& st) {
    // If no chips left, can only CHECK or FOLD; CHECK is never worse
    if (st.a <= 0) {
        return "ACTION CHECK";
    }

    // Sampling plan per round to stay within global budget
    int t = 0;
    if (st.r == 1) t = 20;
    else if (st.r == 2) t = 30;
    else if (st.r == 3) t = 40;
    else t = 60;

    // If budget exhausted, default to conservative CHECK
    if (rate_budget_left <= 0) {
        return "ACTION CHECK";
    }

    auto rates = request_rates(t);
    double w = rates.first, d = rates.second;
    double e = w + 0.5 * d;

    // Thresholds per round (value-heavy)
    double th = 0.62;
    if (st.r == 1) th = 0.62;
    else if (st.r == 2) th = 0.60;
    else if (st.r == 3) th = 0.62;
    else if (st.r == 4) th = 0.64;

    if (e >= th) {
        // All-in maximize value; fold outcome independent of size
        return string("ACTION RAISE ") + to_string(st.a);
    } else {
        return "ACTION CHECK";
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string tok;
    // Initial line: G
    if (!(cin >> tok)) return 0;
    if (tok == "-1") return 0;
    // If it's an integer, it's G; ignore content
    // From here process stream
    while (cin >> tok) {
        if (tok == "-1") {
            return 0;
        } else if (tok == "STATE") {
            State st;
            cin >> st.h >> st.r >> st.a >> st.b >> st.P >> st.k;
            string t2;
            cin >> t2; // "ALICE"
            if (t2 == "-1") return 0;
            // our two hole cards
            cin >> st.as >> st.av >> st.bs >> st.bv;
            string t3;
            cin >> t3; // "BOARD"
            if (t3 == "-1") return 0;
            st.board.clear();
            for (int i = 0; i < st.k; ++i) {
                int s, v;
                cin >> s >> v;
                st.board.emplace_back(s, v);
            }

            string action = decide_action(st);
            cout << action << endl;
            cout.flush();
        } else if (tok == "OPP") {
            string act;
            cin >> act;
            if (act == "-1") return 0;
            if (act == "CALL") {
                int x; cin >> x;
            } else if (act == "CHECK") {
                // nothing
            } else if (act == "FOLD") {
                // nothing
            } else {
                // unknown, ignore
            }
        } else if (tok == "RESULT") {
            int delta;
            cin >> delta;
            // Hand finished, proceed
        } else if (tok == "SCORE") {
            double W;
            cin >> W;
            break;
        } else if (tok == "RATES") {
            // Occasionally, if out of sync, just drain it
            double w, d; cin >> w >> d;
        } else if (tok == "ALICE") {
            // Should only appear within STATE processing; drain line if appears
            int s1, v1, s2, v2;
            cin >> s1 >> v1 >> s2 >> v2;
        } else if (tok == "BOARD") {
            // Should only appear within STATE processing; number of cards unknown here
            // We cannot know k here reliably; skip the rest of line
            string line;
            getline(cin, line);
        } else {
            // Possibly the initial G or stray number; ignore
        }
    }

    return 0;
}