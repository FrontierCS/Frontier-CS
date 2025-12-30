#include <bits/stdc++.h>
using namespace std;

static bool readWord(string &s) {
    if (!(cin >> s)) return false;
    return true;
}

static bool askSet(const vector<int> &S) {
    cout << "? " << (int)S.size();
    for (int x : S) cout << " " << x;
    cout << endl; // flush
    string ans;
    if (!readWord(ans)) exit(0);
    if (ans == "YES") return true;
    if (ans == "NO") return false;
    exit(0);
}

static bool guessX(int g) {
    cout << "! " << g << endl; // flush
    string ans;
    if (!readWord(ans)) exit(0);
    if (ans == ":)") return true;
    if (ans == ":(") return false;
    exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> T, L;
    T.reserve(n);
    for (int i = 1; i <= n; i++) T.push_back(i);

    int questions = 0;

    auto totalSize = [&]() -> int { return (int)T.size() + (int)L.size(); };

    while (questions < 53 && totalSize() > 2) {
        int a = (int)T.size() / 2;
        int b = (int)L.size() / 2;

        vector<int> S;
        S.reserve(a + b);
        for (int i = 0; i < a; i++) S.push_back(T[i]);
        for (int i = 0; i < b; i++) S.push_back(L[i]);

        if (S.empty()) { // should not happen when totalSize()>2, but just in case
            if (!T.empty()) S.push_back(T[0]);
            else if (!L.empty()) S.push_back(L[0]);
        }

        bool yes = askSet(S);

        vector<int> newT, newL;
        if (yes) {
            // newT = Tin + Lin, newL = Tout, Lout eliminated
            newT.reserve(a + b);
            newL.reserve((int)T.size() - a);

            newT.insert(newT.end(), T.begin(), T.begin() + a);
            newT.insert(newT.end(), L.begin(), L.begin() + b);
            newL.insert(newL.end(), T.begin() + a, T.end());
        } else {
            // newT = Tout + Lout, newL = Tin, Lin eliminated
            newT.reserve((int)T.size() - a + (int)L.size() - b);
            newL.reserve(a);

            newT.insert(newT.end(), T.begin() + a, T.end());
            newT.insert(newT.end(), L.begin() + b, L.end());
            newL.insert(newL.end(), T.begin(), T.begin() + a);
        }

        T.swap(newT);
        L.swap(newL);
        questions++;
    }

    vector<int> cand;
    cand.reserve(totalSize());
    cand.insert(cand.end(), T.begin(), T.end());
    cand.insert(cand.end(), L.begin(), L.end());

    if (cand.empty()) {
        // Should be impossible if judge is consistent; fallback.
        guessX(1);
        return 0;
    }

    if ((int)cand.size() == 1) {
        guessX(cand[0]);
        return 0;
    }

    // size >= 2: use up to 2 guesses
    if (guessX(cand[0])) return 0;
    guessX(cand[1]);
    return 0;
}