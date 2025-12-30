#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "! 1" << endl;
        cout.flush();
        return 0;
    }

    const int MAX_Q = 53;
    int questions = 0;

    vector<char> dpT(n + 1, 1), dpL(n + 1, 1);
    vector<char> newT(n + 1), newL(n + 1);
    vector<int> prefA(n + 1), prefC(n + 1);

    auto ask_prefix = [&](int m) -> string {
        cout << "? " << m;
        for (int i = 1; i <= m; ++i) {
            cout << ' ' << i;
        }
        cout << endl;
        cout.flush();
        string resp;
        if (!(cin >> resp)) exit(0);
        return resp;
    };

    auto guess = [&](int x) {
        cout << "! " << x << endl;
        cout.flush();
        string res;
        if (!(cin >> res)) exit(0);
        if (res == ":)") exit(0);
    };

    while (questions < MAX_Q) {
        int totalA = 0, totalC = 0;
        for (int i = 1; i <= n; ++i) {
            int A = dpT[i] ? 1 : 0;
            int C = (dpT[i] || dpL[i]) ? 1 : 0;
            totalA += A;
            totalC += C;
            prefA[i] = totalA;
            prefC[i] = totalC;
        }

        if (totalC <= 2) break;

        int best_m = 1;
        int best_val = totalC;

        for (int m = 1; m <= n; ++m) {
            int prefA_m = prefA[m];
            int prefC_m = prefC[m];
            int P_yes = prefC_m + (totalA - prefA_m);
            int P_no  = prefA_m + (totalC - prefC_m);
            int cur = max(P_yes, P_no);
            if (cur < best_val) {
                best_val = cur;
                best_m = m;
            }
        }

        string resp = ask_prefix(best_m);
        ++questions;

        if (resp == "YES") {
            for (int i = 1; i <= best_m; ++i) {
                newT[i] = (dpT[i] || dpL[i]) ? 1 : 0;
                newL[i] = 0;
            }
            for (int i = best_m + 1; i <= n; ++i) {
                newT[i] = 0;
                newL[i] = dpT[i];
            }
        } else {
            for (int i = 1; i <= best_m; ++i) {
                newT[i] = 0;
                newL[i] = dpT[i];
            }
            for (int i = best_m + 1; i <= n; ++i) {
                newT[i] = (dpT[i] || dpL[i]) ? 1 : 0;
                newL[i] = 0;
            }
        }

        dpT.swap(newT);
        dpL.swap(newL);
    }

    vector<int> cand;
    for (int i = 1; i <= n; ++i) {
        if (dpT[i] || dpL[i]) cand.push_back(i);
    }

    if (cand.empty()) {
        guess(1);
        return 0;
    }

    guess(cand[0]);
    if (cand.size() >= 2) {
        guess(cand[1]);
    }

    return 0;
}