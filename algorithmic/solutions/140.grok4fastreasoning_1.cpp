#include <bits/stdc++.h>
using namespace std;

int main() {
    long long b;
    int k, w;
    cin >> b >> k >> w;
    const long long R = 100000000LL;

    // Query left: (-R, 0)
    cout << "? 1 -100000000 0" << endl;
    cout.flush();
    vector<long long> dl(k);
    for (int i = 0; i < k; i++) {
        cin >> dl[i];
    }

    // Query right: (R, 0)
    cout << "? 1 100000000 0" << endl;
    cout.flush();
    vector<long long> dr(k);
    for (int i = 0; i < k; i++) {
        cin >> dr[i];
    }

    // Query up: (0, R)
    cout << "? 1 0 100000000" << endl;
    cout.flush();
    vector<long long> du(k);
    for (int i = 0; i < k; i++) {
        cin >> du[i];
    }

    // Query down: (0, -R)
    cout << "? 1 0 -100000000" << endl;
    cout.flush();
    vector<long long> dd(k);
    for (int i = 0; i < k; i++) {
        cin >> dd[i];
    }

    vector<pair<long long, long long>> positions;
    vector<tuple<int, int, int, int>> indices_used;
    for (int i = 0; i < k; i++) {
        for (int j = 0; j < k; j++) {
            long long dli = dl[i];
            long long drj = dr[j];
            if ((dli - drj) % 2 != 0) continue;
            long long xx = (dli - drj) / 2;
            if (xx < -b || xx > b) continue;

            long long sum_lr = dli + drj;
            if ((sum_lr - 2 * R) % 2 != 0) continue;
            long long absy_x = (sum_lr - 2 * R) / 2;
            if (absy_x < 0 || absy_x > b) continue;

            for (int p = 0; p < k; p++) {
                for (int q = 0; q < k; q++) {
                    long long dup = du[p];
                    long long ddq = dd[q];
                    if ((ddq - dup) % 2 != 0) continue;
                    long long yy = (ddq - dup) / 2;
                    if (yy < -b || yy > b) continue;

                    long long sum_ud = dup + ddq;
                    if ((sum_ud - 2 * R) % 2 != 0) continue;
                    long long absx_y = (sum_ud - 2 * R) / 2;
                    if (absx_y < 0 || absx_y > b) continue;

                    if (abs(yy) == absy_x && abs(xx) == absx_y) {
                        positions.emplace_back(xx, yy);
                        indices_used.emplace_back(i, j, p, q);
                    }
                }
            }
        }
    }

    // Now, positions should have exactly k entries
    assert((int)positions.size() == k);

    // Output
    cout << "!";
    for (auto& pos : positions) {
        cout << " " << pos.first << " " << pos.second;
    }
    cout << endl;
    cout.flush();

    return 0;
}