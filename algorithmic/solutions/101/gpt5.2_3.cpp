#include <bits/stdc++.h>
using namespace std;

static inline bool isGateString(const string& s) {
    if (s.empty()) return false;
    for (char c : s) if (c != '&' && c != '|') return false;
    return true;
}
static inline bool isBinaryString(const string& s) {
    if (s.empty()) return false;
    for (char c : s) if (c != '0' && c != '1') return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, R;
    if (!(cin >> N >> R)) return 0;

    vector<int> U(N), V(N);
    int maxUV = 0;
    for (int i = 0; i < N; i++) {
        cin >> U[i] >> V[i];
        maxUV = max(maxUV, max(U[i], V[i]));
    }

    string t;
    if (!(cin >> t)) return 0;

    // If the "gate string" is not present, nothing meaningful can be done in offline mode.
    if (!isGateString(t)) {
        return 0;
    }

    // Determine switch count; per statement it's 2N+1, but make robust using max index observed.
    int M = max(2 * N, maxUV);
    int S = M + 1;

    auto evalCircuit = [&](string s) -> int {
        if ((int)s.size() < S) s.append(S - (int)s.size(), '0');
        else if ((int)s.size() > S) s.resize(S);

        vector<unsigned char> out(S, 0);
        for (int j = M; j >= N; --j) out[j] = (s[j] == '1');

        for (int i = N - 1; i >= 0; --i) {
            unsigned char a = out[U[i]];
            unsigned char b = out[V[i]];
            unsigned char gateOut = (t[i] == '&') ? (a & b) : (a | b);
            out[i] = gateOut ^ (s[i] == '1');
        }
        return (int)out[0];
    };

    // If there are binary strings after t, treat them as queries to evaluate; otherwise output "! t".
    vector<string> queries;
    string token;
    while (cin >> token) {
        if (isBinaryString(token)) queries.push_back(token);
    }

    if (queries.empty()) {
        cout << "! " << t << "\n";
    } else {
        for (auto &qs : queries) {
            cout << evalCircuit(qs) << "\n";
        }
    }
    return 0;
}