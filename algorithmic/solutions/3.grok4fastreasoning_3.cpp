#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int sub, n;
    cin >> sub >> n;
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    vector<int> all(n);
    iota(all.begin(), all.end(), 1);
    int kk = min(30, n / 3);
    vector<int> seeds;
    int max_trials = 1000;
    for (int trial = 0; trial < max_trials; ++trial) {
        random_shuffle(all.begin(), all.end());
        vector<int> cand(all.begin(), all.begin() + kk);
        vector<int> seq = cand;
        random_shuffle(seq.begin(), seq.end());
        cout << seq.size();
        for (int x : seq) cout << " " << x;
        cout << "\n";
        cout.flush();
        vector<int> res(seq.size());
        for (int &x : res) cin >> x;
        bool good = true;
        for (int b : res) if (b) {
            good = false;
            break;
        }
        if (good) {
            seeds = cand;
            break;
        }
        if (trial == max_trials - 1) {
            // fallback smaller kk
            kk /= 2;
            trial = -1;
        }
    }
    // now seeds has kk independent labels
    vector<deque<int>> chains;
    set<int> known_set;
    for (int s : seeds) {
        chains.emplace_back(deque<int>{s});
        known_set.insert(s);
    }
    int num_chains = chains.size();
    // now extend until done
    while (known_set.size() < n) {
        // get current ends
        vector<int> ends;
        map<int, pair<int, int>> end_info; // end -> (chain_idx, 0:front 1:back)
        for (int ci = 0; ci < chains.size(); ++ci) {
            int fr = chains[ci].front();
            int bk = chains[ci].back();
            if (find(ends.begin(), ends.end(), fr) == ends.end()) {
                ends.push_back(fr);
                end_info[fr] = {ci, 0};
            }
            if (find(ends.begin(), ends.end(), bk) == ends.end()) {
                ends.push_back(bk);
                end_info[bk] = {ci, 1};
            }
        }
        // now ind check and resolve
        vector<int> current_f = ends;
        bool ind_ok = false;
        while (!ind_ok && !current_f.empty()) {
            vector<int> order = current_f;
            random_shuffle(order.begin(), order.end());
            cout << order.size();
            for (int x : order) cout << " " << x;
            cout << "\n";
            cout.flush();
            vector<int> res_ind(order.size());
            for (int &x : res_ind) cin >> x;
            int hit_pos = -1;
            for (int j = 0; j < res_ind.size(); ++j) {
                if (res_ind[j]) {
                    hit_pos = j;
                    break;
                }
            }
            if (hit_pos == -1) {
                ind_ok = true;
                current_f = order; // ordered
                break;
            }
            // resolve
            int conf = order[hit_pos];
            vector<int> prev_order(order.begin(), order.begin() + hit_pos);
            // batch test conf vs prev_order
            vector<int> seq_m;
            seq_m.push_back(conf);
            for (int p : prev_order) {
                seq_m.push_back(p);
                seq_m.push_back(p);
            }
            seq_m.push_back(conf);
            cout << seq_m.size();
            for (int x : seq_m) cout << " " << x;
            cout << "\n";
            cout.flush();
            vector<int> res_m(seq_m.size());
            for (int &x : res_m) cin >> x;
            // parse
            vector<bool> adjs(prev_order.size(), false);
            int base = 1; // after conf on index 0
            for (int ii = 0; ii < prev_order.size(); ++ii) {
                int fb_idx = base + 2 * ii;
                adjs[ii] = res_m[fb_idx];
            }
            // find the one true
            int target_ii = -1;
            int cnt = 0;
            for (int ii = 0; ii < adjs.size(); ++ii) {
                if (adjs[ii]) {
                    target_ii = ii;
                    ++cnt;
                }
            }
            assert(cnt == 1);
            int target = prev_order[target_ii];
            // now merge chains of conf and target
            auto [c1, s1] = end_info[conf];
            auto [c2, s2] = end_info[target];
            if (c1 == c2) {
                // self loop, impossible
                assert(false);
            }
            // merge c1 and c2 connecting s1 of c1 to s2 of c2 via direct edge
            // orient
            deque<int> ch1 = chains[c1];
            if (s1 == 0) reverse(ch1.begin(), ch1.end());
            deque<int> ch2 = chains[c2];
            if (s2 == 1) reverse(ch2.begin(), ch2.end());
            // now back of ch1 to front of ch2
            for (int x : ch2) ch1.push_back(x);
            chains[c1] = ch1;
            // remove c2
            chains.erase(chains.begin() + c2);
            // now update current_f remove conf and target
            vector<int> new_f;
            for (int ee : current_f) {
                if (ee != conf && ee != target) new_f.push_back(ee);
            }
            current_f = new_f;
            // update end_info not needed since redo
        }
        if (current_f.empty()) {
            // all merged, done?
            break;
        }
        // now extension with current_f ind
        // light current_f random order
        vector<int> light_seq = current_f;
        random_shuffle(light_seq.begin(), light_seq.end());
        // now remain list
        vector<int> remain_l;
        for (int i = 1; i <= n; ++i) {
            if (known_set.find(i) == known_set.end()) remain_l.push_back(i);
        }
        int rsz = remain_l.size();
        // seq
        vector<int> seq = light_seq;
        for (int u : remain_l) {
            seq.push_back(u);
            seq.push_back(u);
        }
        // off light_seq
        for (int f : light_seq) seq.push_back(f);
        cout << seq.size();
        for (int x : seq) cout << " " << x;
        cout << "\n";
        cout.flush();
        vector<int> res(seq.size());
        for (int &x : res) cin >> x;
        // now parse the b for each remain
        vector<int> hit_u;
        int light_sz = light_seq.size();
        for (int ri = 0; ri < rsz; ++ri) {
            int pos_after_on = light_sz + 2 * ri;
            if (res[pos_after_on]) hit_u.push_back(remain_l[ri]);
        }
        // now for each hit_u, match to which in current_f
        int fsz = current_f.size();
        if (!hit_u.empty()) {
            vector<int> match_seq;
            for (int uu : hit_u) {
                match_seq.push_back(uu);
                vector<int> f_order = current_f;
                random_shuffle(f_order.begin(), f_order.end());
                for (int ff : f_order) {
                    match_seq.push_back(ff);
                    match_seq.push_back(ff);
                }
                match_seq.push_back(uu);
            }
            cout << match_seq.size();
            for (int x : match_seq) cout << " " << x;
            cout << "\n";
            cout.flush();
            vector<int> res_match(match_seq.size());
            for (int &x : res_match) cin >> x;
            // now parse for each hit_u
            int mbase = 0;
            for (int hi = 0; hi < hit_u.size(); ++hi) {
                int usize = 1 + 2 * fsz + 1;
                int uu = hit_u[hi];
                // find which f
                vector<int> connected_f;
                int base_pos = mbase + 1; // after uu on
                for (int fi = 0; fi < fsz; ++fi) {
                    int fb_pos = base_pos + 2 * fi;
                    if (res_match[fb_pos]) connected_f.push_back(current_f[fi]);
                }
                mbase += usize;
                // now connected_f size 1 or 2
                assert(connected_f.size() >= 1 && connected_f.size() <= 2);
                for (int cf : connected_f) {
                    // attach uu to cf 's chain
                    auto [ci, si] = end_info[cf]; // need end_info for current_f
                    // wait, end_info is for ends, but current_f is subset if resolved
                    // this is getting tricky, perhaps I need to update end_info after resolve
                    // to simplify, since small, for each connected_f, find which chain and side by checking if front or back of some chain
                    int target_ci = -1;
                    int target_si = -1;
                    for (int cii = 0; cii < chains.size(); ++cii) {
                        if (chains[cii].front() == cf) {
                            target_ci = cii;
                            target_si = 0;
                            break;
                        }
                        if (chains[cii].back() == cf) {
                            target_ci = cii;
                            target_si = 1;
                            break;
                        }
                    }
                    assert(target_ci != -1);
                    // now attach uu to that side
                    if (target_si == 0) {
                        chains[target_ci].push_front(uu);
                    } else {
                        chains[target_ci].push_back(uu);
                    }
                    known_set.insert(uu);
                    // add edge
                    // assume adj vector<vector<int>> adj(n+1);
                    adj[uu].push_back(cf);
                    adj[cf].push_back(uu);
                }
                if (connected_f.size() == 2) {
                    // merge the two chains
                    int ci1 = -1, si1 = -1, ci2 = -1, si2 = -1;
                    // find for first connected_f
                    for (int cii = 0; cii < chains.size(); ++cii) {
                        if (chains[cii].front() == connected_f[0]) {
                            ci1 = cii;
                            si1 = 0;
                            break;
                        }
                        if (chains[cii].back() == connected_f[0]) {
                            ci1 = cii;
                            si1 = 1;
                            break;
                        }
                    }
                    // similar for second
                    for (int cii = 0; cii < chains.size(); ++cii) {
                        if (cii == ci1) continue;
                        if (chains[cii].front() == connected_f[1]) {
                            ci2 = cii;
                            si2 = 0;
                            break;
                        }
                        if (chains[cii].back() == connected_f[1]) {
                            ci2 = cii;
                            si2 = 1;
                            break;
                        }
                    }
                    assert(ci1 != -1 && ci2 != -1);
                    // now merge ci1 and ci2 with u in between
                    // orient so back of ci1 to u to front of ci2
                    deque<int> ch1 = chains[ci1];
                    if (si1 == 0) reverse(ch1.begin(), ch1.end());
                    deque<int> ch2 = chains[ci2];
                    if (si2 == 1) reverse(ch2.begin(), ch2.end());
                    // now append u to ch1 back
                    ch1.push_back(uu);
                    // add edges uu to connected_f[0] and [1], already done
                    // then append ch2 to ch1
                    for (int x : ch2) ch1.push_back(x);
                    // now set chains[ci1] = ch1
                    chains[ci1] = ch1;
                    // remove ci2
                    chains.erase(chains.begin() + ci2);
                }
            }
        }
    }
    // now all known, now final connection
    vector<vector<int>> adj(n + 1);
    // add all known edges from chains
    for (auto &ch : chains) {
        for (int ii = 0; ii + 1 < ch.size(); ++ii) {
            int a = ch[ii], b = ch[ii + 1];
            adj[a].push_back(b);
            adj[b].push_back(a);
        }
    }
    // now collect final ends
    set<int> final_end_set;
    for (auto &ch : chains) {
        if (!ch.empty()) {
            final_end_set.insert(ch.front());
            final_end_set.insert(ch.back());
        }
    }
    vector<int> final_ends(final_end_set.begin(), final_end_set.end());
    int fends = final_ends.size();
    if (fends > 0) {
        // test all pairs
        vector<pair<int, int>> possible_pairs;
        for (int i = 0; i < fends; ++i) {
            for (int j = i + 1; j < fends; ++j) {
                possible_pairs.emplace_back(final_ends[i], final_ends[j]);
            }
        }
        int np = possible_pairs.size();
        vector<int> final_seq;
        for (auto [a, b] : possible_pairs) {
            final_seq.push_back(a);
            final_seq.push_back(b);
            final_seq.push_back(a);
            final_seq.push_back(b);
        }
        cout << final_seq.size();
        for (int x : final_seq) cout << " " << x;
        cout << "\n";
        cout.flush();
        vector<int> res_final(final_seq.size());
        for (int &x : res_final) cin >> x;
        // parse
        for (int pi = 0; pi < np; ++pi) {
            int base = 4 * pi;
            int b_pos = base + 1; // after first a 0, after b = base+1
            if (res_final[b_pos]) {
                int a = possible_pairs[pi].first, b = possible_pairs[pi].second;
                adj[a].push_back(b);
                adj[b].push_back(a);
            }
        }
    }
    // now build the perm from 1
    vector<int> perm;
    int start = 1;
    int curr = start;
    int pre = -1;
    set<int> visited;
    perm.push_back(curr);
    visited.insert(curr);
    while (true) {
        int nxt = -1;
        for (int nb : adj[curr]) {
            if (nb != pre) {
                nxt = nb;
                break;
            }
        }
        if (nxt == -1 || visited.count(nxt)) break;
        pre = curr;
        curr = nxt;
        perm.push_back(curr);
        visited.insert(curr);
        if (curr == start) break;
    }
    // if not full, try other direction
    if (perm.size() < n) {
        perm.clear();
        visited.clear();
        curr = start;
        pre = -1;
        perm.push_back(curr);
        visited.insert(curr);
        // choose the other neighbor
        int other_n = -1;
        for (int nb : adj[start]) {
            if (nb != adj[start][0]) { // arbitrary first
                other_n = nb;
                break;
            }
        }
        pre = adj[start][0]; // the first direction
        curr = other_n;
        perm.push_back(curr);
        visited.insert(curr);
        while (true) {
            int nxt = -1;
            for (int nb : adj[curr]) {
                if (nb != pre) {
                    nxt = nb;
                    break;
                }
            }
            if (nxt == -1 || visited.count(nxt)) break;
            pre = curr;
            curr = nxt;
            perm.push_back(curr);
            visited.insert(curr);
            if (curr == start) break;
        }
    }
    // now perm should have n
    assert(perm.size() == n);
    // output
    cout << -1;
    for (int p : perm) cout << " " << p;
    cout << "\n";
    cout.flush();
    return 0;
}