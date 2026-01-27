#include <bits/stdc++.h>
using namespace std;

static const long long BUDGET_LIMIT = 3000000;
static long long budgetUsed = 0;

static inline vector<string> split(const string &s) {
    vector<string> res;
    string cur;
    istringstream iss(s);
    while (iss >> cur) res.push_back(cur);
    return res;
}

static inline bool getline_safe(string &line) {
    if (!std::getline(cin, line)) return false;
    if (line == "-1") exit(0);
    return true;
}

struct State {
    int h, r;
    long long a, b, P;
    int k;
    int s1, v1, s2, v2;
    vector<pair<int,int>> board;
};

static bool shouldRaisePreflop(int s1, int v1, int s2, int v2) {
    // Values: 1..13 => 2..A
    int high = max(v1, v2), low = min(v1, v2);
    bool suited = (s1 == s2);
    // Any pair
    if (v1 == v2) return true;
    // Any Ace
    if (high == 13) return true;
    // K with T or better (K9+ to be a bit looser)
    if (high == 12 && low >= 9) return true;
    // KQ offsuit
    if ((high == 12 && low == 11)) return true;
    // Suited broadway-ish / suited connectors
    if (suited) {
        // Suited QJ, KJ, QT+
        if ((high >= 11 && low >= 10)) return true;
        // Suited connectors 9T, TJ, QK
        if ((high - low == 1) && low >= 9) return true;
    }
    // Both J or higher
    if (high >= 11 && low >= 11) return true;
    return false;
}

static int suggestedTForK(int k) {
    if (k == 3) return 60;   // flop
    if (k == 4) return 80;   // turn
    if (k == 5) return 120;  // river
    return 0;
}

static double thresholdForK(int k) {
    if (k == 3) return 0.58; // flop
    if (k == 4) return 0.56; // turn
    if (k == 5) return 0.52; // river
    return 1.0; // preflop not used
}

static pair<double,double> askRate(int t) {
    cout << "RATE " << t << endl;
    cout.flush();
    string line;
    while (getline_safe(line)) {
        auto tok = split(line);
        if (tok.empty()) continue;
        if (tok[0] == "RATES" && tok.size() >= 3) {
            double w = atof(tok[1].c_str());
            double d = atof(tok[2].c_str());
            return {w, d};
        }
        // Pass through other lines if any unexpected (shouldn't happen)
    }
    return {0.0,0.0};
}

static void processState(const string &stateLine) {
    // Parse STATE
    auto tks = split(stateLine);
    State st;
    st.h = stoi(tks[1]);
    st.r = stoi(tks[2]);
    st.a = stoll(tks[3]);
    st.b = stoll(tks[4]);
    st.P = stoll(tks[5]);
    st.k = stoi(tks[6]);

    // Read ALICE
    string line;
    getline_safe(line);
    auto tkA = split(line);
    // tkA: ALICE c1 v1 c2 v2
    st.s1 = stoi(tkA[1]);
    st.v1 = stoi(tkA[2]);
    st.s2 = stoi(tkA[3]);
    st.v2 = stoi(tkA[4]);

    // Read BOARD
    getline_safe(line);
    auto tkB = split(line);
    st.board.clear();
    if ((int)tkB.size() >= 1 && tkB[0] == "BOARD") {
        for (size_t i = 1; i + 1 < tkB.size(); i += 2) {
            int cs = stoi(tkB[i]);
            int cv = stoi(tkB[i+1]);
            st.board.push_back({cs, cv});
        }
    }

    // Decide action
    // Never fold; if a == 0 we cannot raise
    if (st.a <= 0) {
        cout << "ACTION CHECK" << endl;
        cout.flush();
        return;
    }

    if (st.k == 0) {
        // Preflop heuristic
        bool raise = shouldRaisePreflop(st.s1, st.v1, st.s2, st.v2);
        if (raise) {
            cout << "ACTION RAISE " << st.a << endl;
        } else {
            cout << "ACTION CHECK" << endl;
        }
        cout.flush();
        return;
    } else {
        // Postflop - use RATE if budget allows
        int wantT = suggestedTForK(st.k);
        int t = 0;
        if (budgetUsed < BUDGET_LIMIT) {
            long long rem = BUDGET_LIMIT - budgetUsed;
            t = (int)min<long long>(wantT, rem);
        }
        double e = 0.0;
        bool haveRate = false;
        if (t > 0) {
            auto rates = askRate(t);
            budgetUsed += t;
            double w = rates.first, d = rates.second;
            e = w + 0.5 * d;
            haveRate = true;
        }
        bool doRaise = false;
        if (haveRate) {
            double thr = thresholdForK(st.k);
            if (e >= thr) doRaise = true;
        } else {
            // No budget: be conservative, only raise with very strong preflop-like board signals?
            // Without evaluation, default to CHECK.
            doRaise = false;
        }

        if (doRaise) {
            cout << "ACTION RAISE " << st.a << endl;
        } else {
            cout << "ACTION CHECK" << endl;
        }
        cout.flush();
        return;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string line;
    if (!getline_safe(line)) return 0;
    // First line should be G, but could be SCORE if match ended or -1
    {
        auto tk = split(line);
        if (tk.empty()) return 0;
        if (tk[0] == "SCORE") return 0;
        // else assume integer
        // no need to store G explicitly
    }

    // Main loop
    do {
        auto tok = split(line);
        if (tok.empty()) continue;
        if (tok[0] == "STATE") {
            processState(line);
        } else if (tok[0] == "RATES") {
            // Should be handled synchronously in askRate; ignore stray
        } else if (tok[0] == "OPP") {
            // OPP CHECK / OPP CALL x / OPP FOLD
            // Nothing to do
        } else if (tok[0] == "RESULT") {
            // RESULT delta - hand ended
            // Nothing special
        } else if (tok[0] == "SCORE") {
            // End of match
            break;
        } else if (tok[0] == "ALICE" || tok[0] == "BOARD") {
            // These should be consumed within processState; ignore if encountered
        } else {
            // Unknown token; ignore
        }
    } while (getline_safe(line));

    return 0;
}