#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

vector<ll> read_distances(int n) {
    vector<ll> res(n);
    for (int i = 0; i < n; ++i) cin >> res[i];
    return res;
}

void send_query(int d, const vector<pair<ll, ll>>& probes) {
    cout << "? " << d;
    for (auto [s, t] : probes) cout << " " << s << " " << t;
    cout << endl;
}

bool all_equal(const vector<ll>& v) {
    for (size_t i = 1; i < v.size(); ++i)
        if (v[i] != v[0]) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ll b;
    int k, w;
    cin >> b >> k >> w;

    // If w is too small, we cannot guarantee full recovery.
    // We fallback to a trivial guess (all deposits at (0,0)).
    if (w < 3) {
        // Use two waves with one probe each at (-b,0) and (b,0).
        // Then output a guess assuming all y are non-negative.
        // This is not optimal, but works for the base constraints.
        send_query(1, {{-b, 0}});
        vector<ll> Da = read_distances(k);
        send_query(1, {{b, 0}});
        vector<ll> Db = read_distances(k);
        sort(Da.begin(), Da.end());
        sort(Db.begin(), Db.end());

        // Try to find a valid matching greedily.
        vector<bool> used(k, false);
        vector<pair<ll, ll>> points;
        for (int i = 0; i < k; ++i) {
            ll da = Da[i];
            int best_j = -1;
            for (int j = 0; j < k; ++j) {
                if (used[j]) continue;
                ll db = Db[j];
                ll sum = da + db - 2 * b;
                if (sum < 0 || sum % 2 != 0) continue;
                ll abs_y = sum / 2;
                if (abs_y > b) continue;
                ll x = (da - db) / 2;
                if (x < -b || x > b) continue;
                best_j = j;
                break;
            }
            if (best_j == -1) break;
            used[best_j] = true;
            ll db = Db[best_j];
            ll sum = da + db - 2 * b;
            ll abs_y = sum / 2;
            ll x = (da - db) / 2;
            // assume y >= 0
            points.emplace_back(x, abs_y);
        }
        if ((int)points.size() != k) {
            points.clear();
            for (int i = 0; i < k; ++i) points.emplace_back(0, 0);
        }
        cout << "!";
        for (auto [x, y] : points) cout << " " << x << " " << y;
        cout << endl;
        return 0;
    }

    // ----- Phase 1: three single-probe waves -----
    send_query(1, {{-b, 0}});
    vector<ll> Da = read_distances(k);
    send_query(1, {{b, 0}});
    vector<ll> Db = read_distances(k);
    send_query(1, {{0, 0}});
    vector<ll> Dc = read_distances(k);

    sort(Da.begin(), Da.end());
    sort(Db.begin(), Db.end());
    sort(Dc.begin(), Dc.end());

    // ----- Phase 2: enumerate candidate multisets (x, |y|) -----
    set<vector<pair<ll, ll>>> candidate_sets;

    // Special case: all distances equal -> all deposits have same (x, |y|)
    if (all_equal(Da) && all_equal(Db)) {
        ll da = Da[0], db = Db[0];
        ll sum = da + db - 2 * b;
        if (sum >= 0 && sum % 2 == 0) {
            ll abs_y = sum / 2;
            ll x = (da - db) / 2;
            if (abs_y <= b && x >= -b && x <= b) {
                vector<pair<ll, ll>> cand(k, {x, abs_y});
                candidate_sets.insert(cand);
            }
        }
    } else {
        // Build adjacency list for bipartite matching Da[i] <-> Db[j]
        int n = k;
        vector<vector<int>> adj(n);
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                ll da = Da[i], db = Db[j];
                ll sum = da + db - 2 * b;
                if (sum < 0 || sum % 2 != 0) continue;
                ll abs_y = sum / 2;
                if (abs_y > b) continue;
                ll x = (da - db) / 2;
                if (x < -b || x > b) continue;
                adj[i].push_back(j);
            }
        }

        // Precompute frequency of Dc distances
        unordered_map<ll, int> dc_freq;
        for (ll d : Dc) dc_freq[d]++;

        // Backtracking to find all perfect matchings consistent with Dc
        vector<pair<ll, ll>> cur_points;
        vector<ll> cur_dists;
        unordered_map<ll, int> pred_freq;
        vector<bool> used_db(n, false);

        function<void(int, int)> backtrack = [&](int i, int start_j) {
            if (i == n) {
                vector<ll> sorted_dists = cur_dists;
                sort(sorted_dists.begin(), sorted_dists.end());
                if (sorted_dists == Dc) {
                    vector<pair<ll, ll>> sorted_points = cur_points;
                    sort(sorted_points.begin(), sorted_points.end());
                    candidate_sets.insert(sorted_points);
                }
                return;
            }
            for (int j : adj[i]) {
                if (used_db[j] || j < start_j) continue;
                ll da = Da[i], db = Db[j];
                ll sum = da + db - 2 * b;
                ll abs_y = sum / 2;
                ll x = (da - db) / 2;
                ll d_pred = llabs(x) + abs_y;

                int cnt_pred = pred_freq[d_pred] + 1;
                auto it = dc_freq.find(d_pred);
                if (it == dc_freq.end() || cnt_pred > it->second) continue;

                used_db[j] = true;
                cur_points.emplace_back(x, abs_y);
                cur_dists.push_back(d_pred);
                pred_freq[d_pred]++;

                int next_start = (i + 1 < n && Da[i + 1] == Da[i]) ? j + 1 : 0;
                backtrack(i + 1, next_start);

                pred_freq[d_pred]--;
                cur_dists.pop_back();
                cur_points.pop_back();
                used_db[j] = false;
            }
        };

        backtrack(0, 0);
    }

    // If no candidate found, create a dummy candidate (should not happen)
    if (candidate_sets.empty()) {
        candidate_sets.insert(vector<pair<ll, ll>>(k, {0, 0}));
    }

    // Convert set to vector for easier processing
    vector<vector<pair<ll, ll>>> candidates(candidate_sets.begin(), candidate_sets.end());

    int waves_used = 3;
    int idx_probe = 0;
    // Predefined list of additional probe positions (enough for k <= 20)
    vector<pair<ll, ll>> extra_probes;
    for (int i = 1; i <= 20; ++i) {
        extra_probes.emplace_back(i, 0);
        extra_probes.emplace_back(0, i);
        extra_probes.emplace_back(i, i);
    }

    // ----- Phase 3: filter candidate multisets with extra waves -----
    while (waves_used < w && candidates.size() > 1) {
        auto [s, t] = extra_probes[idx_probe++];
        send_query(1, {{s, t}});
        vector<ll> D_new = read_distances(k);
        sort(D_new.begin(), D_new.end());
        waves_used++;

        vector<vector<pair<ll, ll>>> new_candidates;
        for (const auto& cand : candidates) {
            bool found = false;
            // Precompute the two possible distances for each point
            vector<pair<ll, ll>> dist_options(k);
            for (int i = 0; i < k; ++i) {
                ll x = cand[i].first;
                ll abs_y = cand[i].second;
                ll d1 = llabs(x - s) + llabs(abs_y - t);
                ll d2 = llabs(x - s) + llabs(-abs_y - t);
                dist_options[i] = {d1, d2};
            }
            // Try all 2^k sign assignments
            for (int mask = 0; mask < (1 << k); ++mask) {
                vector<ll> dists;
                for (int i = 0; i < k; ++i) {
                    ll d = (mask & (1 << i)) ? dist_options[i].second : dist_options[i].first;
                    dists.push_back(d);
                }
                sort(dists.begin(), dists.end());
                if (dists == D_new) {
                    found = true;
                    break;
                }
            }
            if (found) new_candidates.push_back(cand);
        }
        candidates = move(new_candidates);
    }

    // Take the first remaining candidate multiset
    vector<pair<ll, ll>> cand = candidates[0];

    // ----- Phase 4: resolve signs -----
    vector<int> sign_masks;
    int total_masks = 1 << k;
    for (int mask = 0; mask < total_masks; ++mask) sign_masks.push_back(mask);

    while (waves_used < w && sign_masks.size() > 1) {
        auto [s, t] = extra_probes[idx_probe++];
        send_query(1, {{s, t}});
        vector<ll> D_new = read_distances(k);
        sort(D_new.begin(), D_new.end());
        waves_used++;

        vector<int> new_masks;
        for (int mask : sign_masks) {
            vector<ll> dists;
            for (int i = 0; i < k; ++i) {
                ll x = cand[i].first;
                ll abs_y = cand[i].second;
                ll y = (mask & (1 << i)) ? abs_y : -abs_y;
                ll d = llabs(x - s) + llabs(y - t);
                dists.push_back(d);
            }
            sort(dists.begin(), dists.end());
            if (dists == D_new) new_masks.push_back(mask);
        }
        sign_masks = move(new_masks);
    }

    int final_mask = sign_masks[0];
    // Build final answer
    vector<pair<ll, ll>> final_points;
    for (int i = 0; i < k; ++i) {
        ll x = cand[i].first;
        ll abs_y = cand[i].second;
        ll y = (final_mask & (1 << i)) ? abs_y : -abs_y;
        final_points.emplace_back(x, y);
    }

    // Output
    cout << "!";
    for (auto [x, y] : final_points) cout << " " << x << " " << y;
    cout << endl;

    return 0;
}