#include <bits/stdc++.h>
using namespace std;

static inline string up(string s) {
    for (char &c : s) c = char(toupper((unsigned char)c));
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> A, B; // A: last answer was truthful, B: last answer was a lie
    A.reserve(n);
    for (int i = 1; i <= n; i++) A.push_back(i);

    auto ask = [&](int p, int q) -> string {
        cout << "? " << (p + q);
        for (int i = 0; i < p; i++) cout << ' ' << A[i];
        for (int i = 0; i < q; i++) cout << ' ' << B[i];
        cout << '\n';
        cout.flush();

        string ans;
        if (!(cin >> ans)) exit(0);
        ans = up(ans);
        return ans;
    };

    auto guess = [&](int g) -> bool {
        cout << "! " << g << '\n';
        cout.flush();
        string verdict;
        if (!(cin >> verdict)) exit(0);
        return verdict == ":)";
    };

    int queries = 0;
    while ((int)A.size() + (int)B.size() > 2 && queries < 53) {
        int p = (int)A.size() / 2;
        int q = (int)B.size() / 2;
        if (p + q == 0) {
            if (!A.empty()) p = 1;
            else q = 1;
        }

        string ans = ask(p, q);
        queries++;

        vector<int> newA, newB;
        if (ans == "YES") {
            newA.reserve(p + q);
            newA.insert(newA.end(), A.begin(), A.begin() + p);
            newA.insert(newA.end(), B.begin(), B.begin() + q);
            newB.assign(A.begin() + p, A.end());
        } else { // "NO"
            newA.reserve((int)A.size() - p + (int)B.size() - q);
            newA.insert(newA.end(), A.begin() + p, A.end());
            newA.insert(newA.end(), B.begin() + q, B.end());
            newB.assign(A.begin(), A.begin() + p);
        }

        A.swap(newA);
        B.swap(newB);

        if (A.empty() && B.empty()) break;
    }

    vector<int> cand;
    cand.reserve(A.size() + B.size());
    cand.insert(cand.end(), A.begin(), A.end());
    cand.insert(cand.end(), B.begin(), B.end());
    if (cand.empty()) cand.push_back(1);

    if (guess(cand[0])) return 0;
    if (cand.size() >= 2) {
        if (guess(cand[1])) return 0;
    } else {
        // Should not happen; still attempt a safe fallback guess.
        int fallback = (cand[0] == 1 ? 2 : 1);
        if (fallback >= 1 && fallback <= n) guess(fallback);
    }

    return 0;
}