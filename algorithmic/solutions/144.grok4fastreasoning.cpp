#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cout.tie(nullptr);

    int n;
    cin >> n;
    int med_low, med_high;

    // First query: full set
    cout << "0 " << n << " ";
    for (int i = 1; i <= n; ++i) {
        cout << i << " ";
    }
    cout << endl;
    cin >> med_low >> med_high;

    // Initial pairs
    vector<pair<int, int>> init_pairs;
    for (int i = 1; i <= n; i += 2) {
        init_pairs.emplace_back(i, i + 1);
    }
    int num_pairs = init_pairs.size();

    // Process pairs
    vector<vector<int>> mixed;
    vector<vector<int>> both_small_pairs;
    vector<vector<int>> both_large_pairs;
    for (int pp = 0; pp < num_pairs; ++pp) {
        int i1 = init_pairs[pp].first;
        int i2 = init_pairs[pp].second;
        vector<int> qset;
        for (int j = 1; j <= n; ++j) {
            if (j != i1 && j != i2) {
                qset.push_back(j);
            }
        }
        int k = n - 2;
        cout << "0 " << k << " ";
        for (int x : qset) {
            cout << x << " ";
        }
        cout << endl;
        int aa, bb;
        cin >> aa >> bb;
        int num_s;
        if (aa <= med_low && bb >= med_high) {
            num_s = 1;
            mixed.emplace_back(i1, i2);
        } else if (aa <= med_low && bb <= med_low) {
            num_s = 0;
            both_large_pairs.emplace_back(i1, i2);
        } else if (aa >= med_high && bb >= med_high) {
            num_s = 2;
            both_small_pairs.emplace_back(i1, i2);
        } else {
            // Error, assume not happen
            num_s = 1;
            mixed.emplace_back(i1, i2);
        }
    }

    vector<int> all_small_pos;
    vector<int> all_large_pos;
    for (auto& pr : both_small_pairs) {
        all_small_pos.push_back(pr[0]);
        all_small_pos.push_back(pr[1]);
    }
    for (auto& pr : both_large_pairs) {
        all_large_pos.push_back(pr[0]);
        all_large_pos.push_back(pr[1]);
    }

    int mm = mixed.size();
    if (mm < n / 2) {
        // Have known
        int tester = -1;
        bool use_small_tester = !both_small_pairs.empty();
        if (use_small_tester) {
            tester = both_small_pairs[0][0];
        } else {
            tester = both_large_pairs[0][0];
        }
        for (auto& pr : mixed) {
            int i = pr[0], j = pr[1];
            vector<int> excl = {i, tester};
            vector<int> qset;
            for (int jj = 1; jj <= n; ++jj) {
                bool excluded = false;
                for (int ex : excl) {
                    if (jj == ex) {
                        excluded = true;
                        break;
                    }
                }
                if (!excluded) {
                    qset.push_back(jj);
                }
            }
            cout << "0 " << (n - 2) << " ";
            for (int x : qset) {
                cout << x << " ";
            }
            cout << endl;
            int aa, bb;
            cin >> aa >> bb;
            bool i_is_small;
            if (use_small_tester) {
                if (aa <= med_low && bb >= med_high) {
                    i_is_small = false;
                } else {
                    i_is_small = true;
                }
            } else {
                if (aa <= med_low && bb >= med_high) {
                    i_is_small = true;
                } else {
                    i_is_small = false;
                }
            }
            if (i_is_small) {
                all_small_pos.push_back(i);
                all_large_pos.push_back(j);
            } else {
                all_small_pos.push_back(j);
                all_large_pos.push_back(i);
            }
        }
    } else {
        // All mixed, special case
        int idx = 0;
        while (idx < mm) {
            if (idx + 1 < mm) {
                // Two pairs
                vector<int> pr1 = mixed[idx];
                int a = pr1[0], b = pr1[1];
                vector<int> pr2 = mixed[idx + 1];
                int c = pr2[0], d = pr2[1];

                // Query 1: exclude a, c
                vector<int> excl1 = {a, c};
                vector<int> qset1;
                for (int jj = 1; jj <= n; ++jj) {
                    bool ex = false;
                    for (int ex : excl1) if (jj == ex) ex = true;
                    if (!ex) qset1.push_back(jj);
                }
                cout << "0 " << (n - 2) << " ";
                for (int x : qset1) cout << x << " ";
                cout << endl;
                int aa1, bb1;
                cin >> aa1 >> bb1;
                int num1 = 0;
                if (aa1 <= med_low && bb1 >= med_high) num1 = 1;
                else if (aa1 <= med_low && bb1 <= med_low) num1 = 0;
                else if (aa1 >= med_high && bb1 >= med_high) num1 = 2;

                // Query 2: exclude a, d
                vector<int> excl2 = {a, d};
                vector<int> qset2;
                for (int jj = 1; jj <= n; ++jj) {
                    bool ex = false;
                    for (int ex : excl2) if (jj == ex) ex = true;
                    if (!ex) qset2.push_back(jj);
                }
                cout << "0 " << (n - 2) << " ";
                for (int x : qset2) cout << x << " ";
                cout << endl;
                int aa2, bb2;
                cin >> aa2 >> bb2;
                int num2 = 0;
                if (aa2 <= med_low && bb2 >= med_high) num2 = 1;
                else if (aa2 <= med_low && bb2 <= med_low) num2 = 0;
                else if (aa2 >= med_high && bb2 >= med_high) num2 = 2;

                int sum_num = num1 + num2;
                int ha = (sum_num == 3) ? 1 : 0;
                if (ha == 1) {
                    all_small_pos.push_back(a);
                    all_large_pos.push_back(b);
                } else {
                    all_small_pos.push_back(b);
                    all_large_pos.push_back(a);
                }
                int hc = num1 - ha;
                if (hc == 1) {
                    all_small_pos.push_back(c);
                    all_large_pos.push_back(d);
                } else {
                    all_small_pos.push_back(d);
                    all_large_pos.push_back(c);
                }
                idx += 2;
            } else {
                // Last pair
                vector<int> pr = mixed[idx];
                int i = pr[0], j = pr[1];
                int s1 = all_small_pos[0]; // known small from previous
                vector<int> excl = {i, s1};
                vector<int> qset;
                for (int jj = 1; jj <= n; ++jj) {
                    bool ex = false;
                    for (int ex : excl) if (jj == ex) ex = true;
                    if (!ex) qset.push_back(jj);
                }
                cout << "0 " << (n - 2) << " ";
                for (int x : qset) cout << x << " ";
                cout << endl;
                int aa, bb;
                cin >> aa >> bb;
                bool i_is_small = (aa >= med_high && bb >= med_high);
                if (i_is_small) {
                    all_small_pos.push_back(i);
                    all_large_pos.push_back(j);
                } else {
                    all_small_pos.push_back(j);
                    all_large_pos.push_back(i);
                }
                idx += 1;
            }
        }
    }

    // Now find pos m1 in all_small_pos
    auto find_max_pos = [&](vector<int> possible, int low, int high, const vector<int>& larges) -> int {
        while (possible.size() > 3) {
            int ps = possible.size();
            int r = ps / 2;
            vector<int> W(possible.begin(), possible.begin() + r);
            vector<int> Lpad(larges.begin(), larges.begin() + r);
            vector<int> qset = W;
            qset.insert(qset.end(), Lpad.begin(), Lpad.end());
            cout << "0 " << (2 * r) << " ";
            for (int x : qset) cout << x << " ";
            cout << endl;
            int a, b;
            cin >> a >> b;
            if (a == low) {
                possible = std::move(W);
            } else {
                possible.erase(possible.begin(), possible.begin() + r);
            }
        }
        // Now <=3
        if (possible.size() == 1) {
            return possible[0];
        } else if (possible.size() == 2) {
            int x = possible[0];
            int y = possible[1];
            int k = -1;
            for (int pos : all_small_pos) {
                if (pos != x && pos != y) {
                    k = pos;
                    break;
                }
            }
            vector<int> L2 = {all_large_pos[0], all_large_pos[1]};
            vector<int> qset = {x, k, L2[0], L2[1]};
            cout << "0 4 ";
            for (int xx : qset) cout << xx << " ";
            cout << endl;
            int a, b;
            cin >> a >> b;
            return (a == low) ? x : y;
        } else { // 3
            int x = possible[0], y = possible[1], z = possible[2];
            vector<int> L2 = {all_large_pos[0], all_large_pos[1]};
            vector<int> qset = {x, y, L2[0], L2[1]};
            cout << "0 4 ";
            for (int xx : qset) cout << xx << " ";
            cout << endl;
            int a, b;
            cin >> a >> b;
            if (a == low) {
                // Now size 2 on x y
                int xx = x, yy = y;
                int kk = -1;
                for (int pos : all_small_pos) {
                    if (pos != xx && pos != yy) {
                        kk = pos;
                        break;
                    }
                }
                vector<int> LL2 = {all_large_pos[0], all_large_pos[1]};
                vector<int> qqset = {xx, kk, LL2[0], LL2[1]};
                cout << "0 4 ";
                for (int qx : qqset) cout << qx << " ";
                cout << endl;
                int aa, bb;
                cin >> aa >> bb;
                return (aa == low) ? xx : yy;
            } else {
                return z;
            }
        }
    };

    // Find pos m2 in all_large_pos
    auto find_min_pos = [&](vector<int> possible, int high, int low, const vector<int>& smalls) -> int {
        while (possible.size() > 3) {
            int ps = possible.size();
            int r = ps / 2;
            vector<int> Z(possible.begin(), possible.begin() + r);
            vector<int> Spad(smalls.begin(), smalls.begin() + r);
            vector<int> qset = Spad;
            qset.insert(qset.end(), Z.begin(), Z.end());
            cout << "0 " << (2 * r) << " ";
            for (int x : qset) cout << x << " ";
            cout << endl;
            int a, b;
            cin >> a >> b;
            if (b == high) {
                possible = std::move(Z);
            } else {
                possible.erase(possible.begin(), possible.begin() + r);
            }
        }
        if (possible.size() == 1) {
            return possible[0];
        } else if (possible.size() == 2) {
            int u = possible[0];
            int v = possible[1];
            int mm_pos = -1;
            for (int pos : all_large_pos) {
                if (pos != u && pos != v) {
                    mm_pos = pos;
                    break;
                }
            }
            vector<int> S2 = {all_small_pos[0], all_small_pos[1]};
            vector<int> qset = {u, mm_pos};
            qset.insert(qset.end(), S2.begin(), S2.end());
            cout << "0 4 ";
            for (int xx : qset) cout << xx << " ";
            cout << endl;
            int a, b;
            cin >> a >> b;
            return (b == high) ? u : v;
        } else { // 3
            int u = possible[0], v = possible[1], w = possible[2];
            vector<int> S2 = {all_small_pos[0], all_small_pos[1]};
            vector<int> qset = S2;
            qset.push_back(u);
            qset.push_back(v);
            cout << "0 4 ";
            for (int xx : qset) cout << xx << " ";
            cout << endl;
            int a, b;
            cin >> a >> b;
            if (b == high) {
                // size 2 on u v
                int uu = u, vv = v;
                int mmm = -1;
                for (int pos : all_large_pos) {
                    if (pos != uu && pos != vv) {
                        mmm = pos;
                        break;
                    }
                }
                vector<int> SS2 = {all_small_pos[0], all_small_pos[1]};
                vector<int> qqset = {uu, mmm};
                qqset.insert(qqset.end(), SS2.begin(), SS2.end());
                cout << "0 4 ";
                for (int qx : qqset) cout << qx << " ";
                cout << endl;
                int aa, bb;
                cin >> aa >> bb;
                return (bb == high) ? uu : vv;
            } else {
                return w;
            }
        }
    };

    int pos_m1 = find_max_pos(all_small_pos, med_low, med_high, all_large_pos);
    int pos_m2 = find_min_pos(all_large_pos, med_high, med_low, all_small_pos);

    int i1 = min(pos_m1, pos_m2);
    int i2 = max(pos_m1, pos_m2);
    cout << "1 " << i1 << " " << i2 << endl;

    return 0;
}