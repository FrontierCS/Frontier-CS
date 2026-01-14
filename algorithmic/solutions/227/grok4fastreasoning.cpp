#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> p(n);
    for (int &i : p) cin >> i;
    vector<int> groups[4];
    int tails[4] = {-1, -1, n + 1, n + 1};
    bool is_empty[4] = {true, true, true, true};
    const int NEG_INF = -1;
    const int POS_INF = n + 1;
    for (int i = 0; i < n; i++) {
        int x = p[i];
        vector<int> poss;
        for (int g = 0; g < 4; g++) {
            if (is_empty[g]) continue;
            bool can = (g < 2 ? tails[g] < x : tails[g] > x);
            if (can) poss.push_back(g);
        }
        int ch = -1;
        if (!poss.empty()) {
            int min_t_dec = POS_INF + 1;
            ch = -1;
            for (int g : poss) {
                if (g >= 2 && tails[g] < min_t_dec) {
                    min_t_dec = tails[g];
                    ch = g;
                }
            }
            if (ch == -1) {
                int max_t_inc = NEG_INF - 1;
                for (int g : poss) {
                    if (g < 2 && tails[g] > max_t_inc) {
                        max_t_inc = tails[g];
                        ch = g;
                    }
                }
            }
        } else {
            bool pref_dec = (x > n / 2);
            int start_type = pref_dec ? 2 : 0;
            ch = -1;
            for (int j = 0; j < 2; j++) {
                int g = start_type + j;
                if (is_empty[g]) {
                    ch = g;
                    break;
                }
            }
            if (ch == -1) {
                start_type = pref_dec ? 0 : 2;
                for (int j = 0; j < 2; j++) {
                    int g = start_type + j;
                    if (is_empty[g]) {
                        ch = g;
                        break;
                    }
                }
            }
            if (ch == -1) {
                ch = 0;
            }
            if (is_empty[ch]) is_empty[ch] = false;
        }
        groups[ch].push_back(x);
        tails[ch] = x;
    }
    cout << groups[0].size() << " " << groups[2].size() << " " << groups[1].size() << " " << groups[3].size() << endl;
    int order[4] = {0, 2, 1, 3};
    for (int k = 0; k < 4; k++) {
        int vec = order[k];
        for (int val : groups[vec]) {
            cout << val << " ";
        }
        cout << endl;
    }
    return 0;
}