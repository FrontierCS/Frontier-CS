#include <bits/stdc++.h>
using namespace std;

int ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    cout.flush();
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

void answer(int x) {
    cout << "! " << x << endl;
    cout.flush();
}

void solve() {
    int n;
    cin >> n;
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);
    vector<int> discarded;
    int a = -1, b = -1, rab = -1, rba = -1;
    bool found_asymmetric = false;

    while (candidates.size() >= 2 && !found_asymmetric) {
        a = candidates.back(); candidates.pop_back();
        b = candidates.back(); candidates.pop_back();
        rab = ask(a, b);
        rba = ask(b, a);
        if (rab == rba) {
            discarded.push_back(a);
            discarded.push_back(b);
        } else {
            found_asymmetric = true;
        }
    }

    int impostor;
    if (found_asymmetric) {
        int c;
        if (!discarded.empty()) {
            c = discarded[0];
        } else if (!candidates.empty()) {
            c = candidates.back();
        } else {
            for (int i = 1; i <= n; ++i) {
                if (i != a && i != b) {
                    c = i;
                    break;
                }
            }
        }
        int rac = ask(a, c);
        int rbc = ask(b, c);
        int zero_player, one_player;
        if (rab == 0 && rba == 1) {
            zero_player = a;
            one_player = b;
        } else {
            zero_player = b;
            one_player = a;
        }
        if (rac != rbc) {
            impostor = zero_player;
        } else {
            impostor = one_player;
        }
    } else {
        if (candidates.size() == 1) {
            impostor = candidates.back();
        } else {
            // Should not happen for valid inputs.
            impostor = 1;
        }
    }
    answer(impostor);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}