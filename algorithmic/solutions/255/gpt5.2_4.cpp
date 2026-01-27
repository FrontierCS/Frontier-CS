#include <bits/stdc++.h>
using namespace std;

static int ask(const vector<int>& L, const vector<int>& R) {
    cout << "? " << (int)L.size() << " " << (int)R.size() << "\n";
    for (int i = 0; i < (int)L.size(); i++) {
        if (i) cout << ' ';
        cout << L[i];
    }
    cout << "\n";
    for (int i = 0; i < (int)R.size(); i++) {
        if (i) cout << ' ';
        cout << R[i];
    }
    cout << "\n";
    cout.flush();

    int F;
    if (!(cin >> F)) exit(0);
    if (abs(F) > 1) exit(0);
    return F;
}

static int ask_single(int a, int b) {
    vector<int> L = {a};
    vector<int> R = {b};
    return ask(L, R);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) return 0;
        if (n < 0) return 0;

        vector<int> L;
        L.push_back(1);

        int ref = -1;
        for (int i = 2; i <= n; i++) {
            vector<int> R = {i};
            int F = ask(L, R);
            if (F == 0) {
                L.push_back(i);
            } else {
                ref = i;
                break;
            }
        }
        if (ref == -1) exit(0);

        vector<int> demag;
        for (int i = 1; i <= n; i++) {
            if (i == ref) continue;
            int F = ask_single(ref, i);
            if (F == 0) demag.push_back(i);
        }

        cout << "! " << demag.size();
        for (int x : demag) cout << " " << x;
        cout << "\n";
        cout.flush();
    }
    return 0;
}