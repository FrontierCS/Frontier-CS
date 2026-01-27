#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    // Random generator
    std::mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());

    vector<int> C(n);
    iota(C.begin(), C.end(), 1);

    auto ask = [&](const vector<int>& S) -> string {
        cout << "? " << (int)S.size();
        for (int x : S) cout << " " << x;
        cout << "\n" << flush;
        string ans;
        if (!(cin >> ans)) exit(0);
        return ans;
    };

    auto guess = [&](int g) -> bool {
        cout << "! " << g << "\n" << flush;
        string res;
        if (!(cin >> res)) exit(0);
        return res == ":)";
    };

    if (n == 1) {
        guess(1);
        return 0;
    }

    vector<char> markPrev(n + 1, 0), markCurr(n + 1, 0);

    // Initial question
    vector<int> S_prev;
    S_prev.reserve(C.size());
    for (int y : C) {
        if (rng() & 1) {
            S_prev.push_back(y);
            markPrev[y] = 1;
        }
    }
    if (S_prev.empty()) {
        int y = C[rng() % C.size()];
        S_prev.push_back(y);
        markPrev[y] = 1;
    } else if ((int)S_prev.size() == (int)C.size()) {
        int idx = rng() % C.size();
        int y = C[idx];
        // Remove y from S_prev
        markPrev[y] = 0;
        S_prev.clear();
        for (int z : C) if (markPrev[z]) S_prev.push_back(z);
    }

    int queriesUsed = 0;
    string a_prev = ask(S_prev);
    ++queriesUsed;

    // Iteratively reduce candidates using sliding pair guarantee
    while ((int)C.size() > 1 && queriesUsed < 53) {
        // Build current random subset S
        vector<int> S;
        S.reserve(C.size());
        for (int y : C) {
            if (rng() & 1) {
                S.push_back(y);
                markCurr[y] = 1;
            }
        }
        if (S.empty()) {
            int y = C[rng() % C.size()];
            S.push_back(y);
            markCurr[y] = 1;
        } else if ((int)S.size() == (int)C.size()) {
            int idx = rng() % C.size();
            int y = C[idx];
            markCurr[y] = 0;
            S.clear();
            for (int z : C) if (markCurr[z]) S.push_back(z);
        }

        string a_curr = ask(S);
        ++queriesUsed;

        bool yesPrev = (a_prev == "YES");
        bool yesCurr = (a_curr == "YES");

        vector<int> newC;
        newC.reserve(C.size());
        for (int y : C) {
            bool keep = ((bool)markPrev[y] == yesPrev) || ((bool)markCurr[y] == yesCurr);
            if (keep) newC.push_back(y);
        }
        C.swap(newC);

        // Prepare for next iteration
        // markPrev becomes markCurr on current C
        for (int y : C) markPrev[y] = markCurr[y];
        // reset markCurr
        fill(markCurr.begin(), markCurr.end(), 0);
        a_prev = a_curr;
        
        if (C.empty()) break;
    }

    if (C.empty()) {
        // Fallback (shouldn't happen with consistent judge)
        guess(1);
        return 0;
    }

    if ((int)C.size() == 1) {
        guess(C[0]);
        return 0;
    }

    // If two or more remain (very unlikely), use up to two guesses
    int guesses = 0;
    for (int i = 0; i < (int)C.size() && guesses < 2; ++i) {
        if (guess(C[i])) return 0;
        ++guesses;
    }
    return 0;
}