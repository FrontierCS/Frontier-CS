#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    auto guess = [&](int g) {
        cout << "! " << g << endl;
        cout.flush();
        string resp;
        if (!(cin >> resp)) exit(0);
        if (resp == ":)") exit(0);
    };

    if (n == 1) {
        guess(1);
        return 0;
    }

    const int MAX_Q = 53;
    int qcnt = 0;
    int gcnt = 0;

    vector<int> cand(n);
    iota(cand.begin(), cand.end(), 1);

    vector<char> canTrue(n + 1, 1), canLie(n + 1, 1);
    vector<char> inS(n + 1);

    while ((int)cand.size() > 1 && qcnt < MAX_Q) {
        int k = (int)cand.size();
        int half = k / 2;
        if (half == 0) half = 1;
        if (half == k) half = k - 1;

        vector<int> Svec;
        Svec.reserve(half);
        for (int i = 0; i < k && (int)Svec.size() < half; ++i) {
            Svec.push_back(cand[i]);
        }

        fill(inS.begin(), inS.end(), 0);
        for (int v : Svec) inS[v] = 1;

        cout << "? " << Svec.size();
        for (int v : Svec) cout << " " << v;
        cout << endl;
        cout.flush();

        string ans;
        if (!(cin >> ans)) return 0;
        bool yes = (ans == "YES");
        ++qcnt;

        vector<int> newCand;
        newCand.reserve(cand.size());
        for (int v : cand) {
            bool T = inS[v];
            bool prevT = canTrue[v];
            bool prevL = canLie[v];

            bool curT = false, curL = false;
            if (yes == T) {
                if (prevT || prevL) curT = true;
            }
            if (yes != T) {
                if (prevT) curL = true;
            }

            if (curT || curL) {
                newCand.push_back(v);
                canTrue[v] = curT;
                canLie[v] = curL;
            } else {
                canTrue[v] = canLie[v] = 0;
            }
        }
        cand.swap(newCand);
    }

    int finalGuess = cand.empty() ? 1 : cand[0];
    cout << "! " << finalGuess << endl;
    cout.flush();

    string resp;
    if (!(cin >> resp)) return 0;
    if (resp == ":)") return 0;

    // Second guess if first was wrong and we still have options
    if (cand.size() >= 2) {
        int second = cand[1];
        cout << "! " << second << endl;
        cout.flush();
        cin >> resp;
    } else {
        int second = (finalGuess == 1 ? 2 : 1);
        cout << "! " << second << endl;
        cout.flush();
        cin >> resp;
    }

    return 0;
}