#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        vector<vector<int>> small_groups;
        int ref = -1;
        int i = 1;
        while (i <= n) {
            vector<int> grp;
            grp.push_back(i);
            int j = (i + 1 <= n ? i + 1 : 0);
            int f = 0;
            if (j != 0) {
                vector<int> le = {i};
                vector<int> ri = {j};
                cout << "? 1 1" << endl;
                cout << i << endl;
                cout << j << endl;
                cout.flush();
                cin >> f;
                if (abs(f) == 1) {
                    ref = i;
                } else {
                    grp.push_back(j);
                    small_groups.push_back(grp);
                }
            } else {
                small_groups.push_back(grp);
            }
            i += 2;
        }
        vector<int> demag;
        auto do_query = [&](const vector<int>& left, const vector<int>& right) -> int {
            int l = left.size();
            int r = right.size();
            cout << "? " << l << " " << r << endl;
            for (int x : left) cout << x << " ";
            cout << endl;
            for (int x : right) cout << x << " ";
            cout << endl;
            cout.flush();
            int f;
            cin >> f;
            return f;
        };
        if (ref != -1) {
            // process small_groups
            for (auto& grp : small_groups) {
                if (grp.size() == 1) {
                    int ff = do_query({ref}, grp);
                    if (ff == 0) {
                        demag.push_back(grp[0]);
                    }
                } else {
                    int ff = do_query({ref}, grp);
                    if (ff == 0) {
                        demag.push_back(grp[0]);
                        demag.push_back(grp[1]);
                    } else {
                        int f1 = do_query({ref}, {grp[0]});
                        if (f1 == 0) {
                            demag.push_back(grp[0]);
                        } else {
                            demag.push_back(grp[1]);
                        }
                    }
                }
            }
        } else {
            // hierarchical to find ref
            vector<vector<int>> current_groups = small_groups;
            bool found_ref = false;
            while (!found_ref) {
                int mm = current_groups.size();
                vector<vector<int>> next_level;
                bool this_found = false;
                for (int k = 0; k < mm / 2; k++) {
                    vector<int> ga = current_groups[2 * k];
                    vector<int> gb = current_groups[2 * k + 1];
                    int f = do_query(ga, gb);
                    if (abs(f) == 1) {
                        this_found = true;
                        // binary search in ga using gb as ref_group
                        vector<int> search = ga;
                        vector<int> ref_group = gb;
                        while (search.size() > 1) {
                            int half = search.size() / 2;
                            vector<int> h1(search.begin(), search.begin() + half);
                            vector<int> h2(search.begin() + half, search.end());
                            int ff = do_query(ref_group, h1);
                            if (ff != 0) {
                                search = h1;
                            } else {
                                search = h2;
                            }
                        }
                        ref = search[0];
                        found_ref = true;
                        break;
                    } else {
                        vector<int> combined = ga;
                        combined.insert(combined.end(), gb.begin(), gb.end());
                        next_level.push_back(combined);
                    }
                }
                if (mm % 2 == 1) {
                    next_level.push_back(current_groups.back());
                }
                if (this_found) {
                    break;
                }
                current_groups = next_level;
            }
            // now ref set, process small_groups
            for (auto& grp : small_groups) {
                if (grp.size() == 1) {
                    int ff = do_query({ref}, grp);
                    if (ff == 0) {
                        demag.push_back(grp[0]);
                    }
                } else {
                    int ff = do_query({ref}, grp);
                    if (ff == 0) {
                        demag.push_back(grp[0]);
                        demag.push_back(grp[1]);
                    } else {
                        int f1 = do_query({ref}, {grp[0]});
                        if (f1 == 0) {
                            demag.push_back(grp[0]);
                        } else {
                            demag.push_back(grp[1]);
                        }
                    }
                }
            }
        }
        // output
        cout << "! " << demag.size();
        for (int z : demag) {
            cout << " " << z;
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}