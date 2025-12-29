#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <deque>

using namespace std;

struct Group {
    int l, r;
    int e1, e2; // e1 most recent, e2 second most recent. -1 if not present.

    int size() const { return r - l + 1; }
    bool sameHistory(const Group& other) const {
        return e1 == other.e1 && e2 == other.e2;
    }
};

bool appendAndCheck(Group& g, int new_e) {
    if (g.e2 == -1 && g.e1 == -1) {
        g.e1 = new_e;
        return true;
    } else if (g.e2 == -1) {
        g.e2 = g.e1;
        g.e1 = new_e;
        return true;
    } else {
        // check three consecutive
        if (g.e2 == g.e1 && g.e1 == new_e) {
            return false; // eliminated
        }
        g.e2 = g.e1;
        g.e1 = new_e;
        return true;
    }
}

void processQuery(int L, int R, int x, vector<Group>& groups) {
    int sz = R - L + 1;
    vector<Group> new_groups;
    for (Group g : groups) {
        if (g.r < L || g.l > R) {
            // completely outside
            int new_e = sz - x;
            Group ng = g;
            if (appendAndCheck(ng, new_e)) {
                new_groups.push_back(ng);
            }
        } else if (g.l >= L && g.r <= R) {
            // completely inside
            int new_e = x - (sz - 1);
            Group ng = g;
            if (appendAndCheck(ng, new_e)) {
                new_groups.push_back(ng);
            }
        } else {
            // overlapping: split into inside and outside parts
            // left outside
            if (g.l < L) {
                Group ng = g;
                ng.r = L - 1;
                int new_e = sz - x;
                if (appendAndCheck(ng, new_e)) {
                    new_groups.push_back(ng);
                }
            }
            // inside part
            int in_l = max(g.l, L);
            int in_r = min(g.r, R);
            Group ng_in = g;
            ng_in.l = in_l;
            ng_in.r = in_r;
            int new_e_in = x - (sz - 1);
            if (appendAndCheck(ng_in, new_e_in)) {
                new_groups.push_back(ng_in);
            }
            // right outside
            if (g.r > R) {
                Group ng = g;
                ng.l = R + 1;
                int new_e = sz - x;
                if (appendAndCheck(ng, new_e)) {
                    new_groups.push_back(ng);
                }
            }
        }
    }

    // sort by left endpoint
    sort(new_groups.begin(), new_groups.end(),
         [](const Group& a, const Group& b) { return a.l < b.l; });

    // merge adjacent groups with same history
    vector<Group> merged;
    for (const Group& g : new_groups) {
        if (merged.empty()) {
            merged.push_back(g);
        } else {
            Group& last = merged.back();
            if (last.r + 1 == g.l && last.sameHistory(g)) {
                last.r = g.r; // merge
            } else {
                merged.push_back(g);
            }
        }
    }
    groups = merged;
}

void solve() {
    int n;
    cin >> n;
    vector<Group> groups;
    groups.push_back({1, n, -1, -1});
    int total_candidates = n;
    int query_count = 0;
    double log_n = log(n);
    double log_base = log(1.116);
    int max_queries = 2 * ceil(log_n / log_base);

    while (total_candidates > 2 && query_count < max_queries) {
        // choose query interval that splits candidates roughly in half
        int total = total_candidates;
        int half = total / 2;
        int cum = 0;
        int L = groups[0].l;
        int R = -1;
        for (const Group& g : groups) {
            int s = g.size();
            if (cum + s > half) {
                int target = half - cum; // how many to take from this group
                R = g.l + target - 1;
                break;
            }
            cum += s;
        }
        if (R == -1) {
            R = groups.back().r;
        }

        cout << "? " << L << " " << R << endl;
        cout.flush();
        int x;
        cin >> x;
        query_count++;

        processQuery(L, R, x, groups);

        total_candidates = 0;
        for (const Group& g : groups) {
            total_candidates += g.size();
        }
    }

    // collect up to two candidates
    vector<int> candidates;
    for (const Group& g : groups) {
        candidates.push_back(g.l);
        if (candidates.size() >= 2) break;
    }

    for (int cand : candidates) {
        cout << "! " << cand << endl;
        cout.flush();
        int resp;
        cin >> resp;
        if (resp == 1) {
            break;
        }
    }
    cout << "#" << endl;
    cout.flush();
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