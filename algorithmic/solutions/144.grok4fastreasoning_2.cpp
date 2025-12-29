#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    int L = n / 2;
    int H = L + 1;
    vector<pair<int, int>> pairs;
    for (int i = 1; i <= n; i += 2) {
        pairs.emplace_back(i, i + 1);
    }
    int num_pairs = pairs.size();
    vector<pair<int, int>> responses(num_pairs, {0, 0});
    for (int j = 0; j < num_pairs; j++) {
        auto [a, b] = pairs[j];
        cout << 0 << " " << n - 2;
        for (int idx = 1; idx <= n; idx++) {
            if (idx != a && idx != b) {
                cout << " " << idx;
            }
        }
        cout << endl;
        cout.flush();
        int m1, m2;
        cin >> m1 >> m2;
        responses[j] = {m1, m2};
    }
    int low_j = -1;
    for (int j = 0; j < num_pairs; j++) {
        int m2 = responses[j].second;
        if (m2 >= H) {
            low_j = j;
            break;
        }
    }
    auto [x, y] = pairs[low_j];
    int z = 1;
    if (z == x || z == y) z = (x == 1 || y == 1 ? 4 : 1);
    cout << 0 << " " << n - 2;
    for (int idx = 1; idx <= n; idx++) {
        if (idx != x && idx != z) {
            cout << " " << idx;
        }
    }
    cout << endl;
    cout.flush();
    int mm1, mm2;
    cin >> mm1 >> mm2;
    int low_pos, high_pos;
    int m2_low = responses[low_j].second;
    bool both = (m2_low > H);
    if (both) {
        if (mm2 >= H) {
            low_pos = x;
            high_pos = y;
        } else {
            low_pos = y;
            high_pos = x;
        }
    } else {
        if (mm2 >= H) {
            low_pos = x;
        } else {
            low_pos = y;
        }
        int high_j = -1;
        for (int jj = 0; jj < num_pairs; jj++) {
            if (jj == low_j) continue;
            auto [m1j, m2j] = responses[jj];
            if (m1j < L && m2j < L) {
                high_j = jj;
                break;
            }
        }
        if (high_j != -1) {
            auto [p, q] = pairs[high_j];
            int zz = 1;
            if (zz == p || zz == q || zz == low_pos) zz = (p == 1 || q == 1 || low_pos == 1 ? 4 : 1);
            cout << 0 << " " << n - 2;
            for (int idx = 1; idx <= n; idx++) {
                if (idx != p && idx != low_pos) {
                    cout << " " << idx;
                }
            }
            cout << endl;
            cout.flush();
            int mmm1, mmm2;
            cin >> mmm1 >> mmm2;
            if (mmm2 > H) {
                high_pos = p;
            } else {
                high_pos = q;
            }
        } else {
            vector<int> suspects;
            for (int jj = 0; jj < num_pairs; jj++) {
                if (jj == low_j) continue;
                int m2j = responses[jj].second;
                if (m2j == L) {
                    auto [pp, qq] = pairs[jj];
                    suspects.push_back(pp);
                    suspects.push_back(qq);
                }
            }
            high_pos = -1;
            for (int posi : suspects) {
                cout << 0 << " " << n - 2;
                for (int idx = 1; idx <= n; idx++) {
                    if (idx != low_pos && idx != posi) {
                        cout << " " << idx;
                    }
                }
                cout << endl;
                cout.flush();
                int m1t, m2t;
                cin >> m1t >> m2t;
                if (m2t > H) {
                    high_pos = posi;
                    break;
                }
            }
        }
    }
    if (low_pos > high_pos) swap(low_pos, high_pos);
    cout << 1 << " " << low_pos << " " << high_pos << endl;
    cout.flush();
    return 0;
}