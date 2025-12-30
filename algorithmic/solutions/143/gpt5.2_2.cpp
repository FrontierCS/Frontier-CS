#include <bits/stdc++.h>
using namespace std;

static inline bool readToken(string &s) {
    if (!(cin >> s)) return false;
    if (s == "-1") exit(0);
    return true;
}

static inline long long readLL() {
    string s;
    readToken(s);
    return stoll(s);
}

static inline double readDouble() {
    string s;
    readToken(s);
    return stod(s);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string tok;
    if (!readToken(tok)) return 0;
    int G = stoi(tok);

    const long long BUDGET = 3'000'000;
    long long used = 0;

    int perHandBudget = (int)floor((double)BUDGET / max(1, G) * 0.70);
    perHandBudget = max(120, min(800, perHandBudget));

    const double weights[4]   = {0.80, 1.00, 1.10, 1.10}; // sum = 4.00
    const double stageMult[4] = {0.70, 0.95, 1.15, 1.35};
    const double capFrac[4]   = {0.35, 0.55, 0.75, 1.00};

    while (readToken(tok)) {
        if (tok == "STATE") {
            long long h = readLL();
            int r = (int)readLL();
            long long a = readLL();
            long long b = readLL();
            long long P = readLL();
            int k = (int)readLL();

            // ALICE line
            readToken(tok); // "ALICE"
            long long as1 = readLL(), av1 = readLL(), as2 = readLL(), av2 = readLL();
            (void)as1; (void)av1; (void)as2; (void)av2;

            // BOARD line
            readToken(tok); // "BOARD"
            for (int i = 0; i < 2 * k; i++) (void)readLL();

            long long remainingBudget = BUDGET - used;
            int tWant = (int)llround(perHandBudget * weights[r - 1] / 4.0);
            tWant = max(10, min(250, tWant));
            int t = 0;
            if (remainingBudget > 0) t = (int)min<long long>(tWant, remainingBudget);

            double w = 0.0, d = 0.0, E = 0.5;
            bool haveRates = false;

            if (t > 0) {
                cout << "RATE " << t << endl;
                used += t;

                readToken(tok); // "RATES"
                w = readDouble();
                d = readDouble();
                E = w + 0.5 * d;
                haveRates = true;
            }

            auto doCheck = [&]() {
                cout << "ACTION CHECK" << endl;
            };

            if (!haveRates || a <= 0) {
                doCheck();
                continue;
            }

            // Conservative threshold early, more aggressive late.
            double thr = 0.5 + 0.5 / sqrt((double)t) - 0.02 * (r - 1);
            thr = max(0.505, min(0.62, thr));

            if (E <= thr) {
                doCheck();
                continue;
            }

            // Bet sizing heuristic.
            double strength = (E - 0.5) * 2.0; // 0..1 when E in [0.5..1.0]
            if (strength < 0.0) strength = 0.0;
            if (strength > 1.0) strength = 1.0;

            double mult = 0.70 + 2.60 * strength; // 0.70..3.30
            double raw = (double)P * mult * stageMult[r - 1];

            int x = (int)llround(raw);
            int minRaise = max(1, (int)floor(0.40 * (double)P));
            x = max(x, minRaise);

            long long cap = (long long)floor((double)a * capFrac[r - 1]);
            if (r == 4) cap = a;
            cap = max(1LL, min(cap, a));
            x = (int)min<long long>(x, cap);

            // Ensure meaningful sizing later streets when strong.
            if (r == 3) {
                double desiredFrac = 0.12 + 0.50 * strength; // 0.12..0.62
                int x2 = (int)floor((double)a * desiredFrac);
                x = max(x, x2);
            } else if (r == 4) {
                double desiredFrac = 0.25 + 0.75 * strength; // 0.25..1.00
                int x2 = (int)floor((double)a * desiredFrac);
                x = max(x, x2);
                if (E > 0.86) x = (int)a;
            }

            x = max(1, min<long long>(x, a));
            cout << "ACTION RAISE " << x << endl;
        } else if (tok == "OPP") {
            readToken(tok); // CHECK/FOLD/CALL
            if (tok == "CALL") {
                (void)readLL(); // x
            }
        } else if (tok == "RESULT") {
            (void)readLL(); // delta
        } else if (tok == "SCORE") {
            (void)readDouble();
            break;
        } else if (tok == "RATES") {
            // Shouldn't happen (we read it synchronously), but consume if it does.
            (void)readDouble();
            (void)readDouble();
        } else {
            // Unknown token; ignore.
        }
    }

    return 0;
}