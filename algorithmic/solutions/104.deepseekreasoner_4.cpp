#include <bits/stdc++.h>
using namespace std;

const int MAXN = 100000;
int state[MAXN + 1];
int trans[4][2];

void init_trans() {
    // state index: 0:00, 1:01, 2:10, 3:11
    // trans[s][H] -> new state index, -1 if forbidden
    trans[0][0] = -1; trans[0][1] = 1;
    trans[1][0] = 2;  trans[1][1] = 3;
    trans[2][0] = 0;  trans[2][1] = 1;
    trans[3][0] = 2;  trans[3][1] = -1;
}

int main() {
    init_trans();
    int t;
    cin >> t;
    while (t--) {
        int n;
        cin >> n;
        vector<int> cands;
        for (int a = 1; a <= n; ++a) {
            state[a] = 15; // all 4 states possible
            cands.push_back(a);
        }
        // cands is already sorted
        while (cands.size() > 2) {
            int k = cands.size();
            int r_val = cands[k / 2]; // median candidate
            cout << "? 1 " << r_val << endl;
            cout.flush();
            int x;
            cin >> x;
            int R = (x == r_val) ? 1 : 0; // 1 for P, 0 for N
            vector<int> new_cands;
            for (int a : cands) {
                int C = (a <= r_val) ? 1 : 0;
                int H = R ^ C;
                int new_mask = 0;
                int old_mask = state[a];
                for (int s = 0; s < 4; ++s) {
                    if ((old_mask >> s) & 1) {
                        int ns = trans[s][H];
                        if (ns != -1) {
                            new_mask |= (1 << ns);
                        }
                    }
                }
                if (new_mask) {
                    state[a] = new_mask;
                    new_cands.push_back(a);
                }
            }
            cands = move(new_cands);
        }
        bool found = false;
        for (int i = 0; i < (int)cands.size() && i < 2; ++i) {
            int a = cands[i];
            cout << "! " << a << endl;
            cout.flush();
            int y;
            cin >> y;
            if (y == 1) {
                found = true;
                break;
            }
        }
        cout << "#" << endl;
        cout.flush();
    }
    return 0;
}