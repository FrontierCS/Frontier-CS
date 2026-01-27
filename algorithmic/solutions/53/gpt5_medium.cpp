#include <bits/stdc++.h>
using namespace std;

static mt19937 rng(712367);

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;
        
        auto ask = [&](const vector<int>& q)->int{
            cout << "?";
            for (int i = 0; i < n; ++i) {
                cout << " " << q[i];
            }
            cout << "\n";
            cout.flush();
            int res;
            if (!(cin >> res)) exit(0);
            if (res == -1) exit(0);
            return res;
        };
        
        int k = 1; // fixed index position we will always put value x at
        cout << k << "\n";
        cout.flush();
        
        int x = 1; // value we will keep at position k in every query
        
        vector<int> p(n+1, 0);
        vector<int> used_val(n+1, 0);
        
        auto build_query = [&](int i, const vector<char>& bit_for_v, int mode)->vector<int>{
            // mode 0: A, i, B
            // mode 1: A, B, i
            // Build list L excluding x, with specified order
            vector<int> A, B;
            A.reserve(n);
            B.reserve(n);
            for (int v = 1; v <= n; ++v) {
                if (v == i || v == x) continue;
                if (bit_for_v[v]) B.push_back(v);
                else A.push_back(v);
            }
            vector<int> L;
            L.reserve(n-1);
            if (mode == 0) {
                // A, i, B
                for (int v: A) L.push_back(v);
                L.push_back(i);
                for (int v: B) L.push_back(v);
            } else {
                // A, B, i
                for (int v: A) L.push_back(v);
                for (int v: B) L.push_back(v);
                L.push_back(i);
            }
            // Fill permutation q: place x at position k, and fill other positions with L in order
            vector<int> q(n);
            int ptr = 0;
            for (int pos = 1; pos <= n; ++pos) {
                if (pos == k) q[pos-1] = x;
                else {
                    q[pos-1] = L[ptr++];
                }
            }
            return q;
        };
        
        int assigned = 0;
        auto mark_assign = [&](int u, int v){
            if (p[u] == 0) {
                p[u] = v;
                if (!used_val[v]) {
                    used_val[v] = 1;
                }
                assigned++;
            }
        };
        
        // Main process: resolve pairs, skipping x (as it will be assigned when its preimage case appears)
        while (assigned < n) {
            int i = -1;
            for (int v = 1; v <= n; ++v) {
                if (p[v] == 0 && v != x) { i = v; break; }
            }
            if (i == -1) break; // only possibly x left
            
            // Tlist is implicitly all v != i, v != x
            // We'll generate random bit dimensions incrementally
            vector<vector<char>> bits; // bits[t][v] in {0,1} for v=1..n, undefined (0) for v==i or v==x
            vector<int> delta; // delta[t] = ans1 - ans0
            const int MAX_M = 10; // keep within 10*n cap overall
            
            auto try_decode = [&](int nbits, int &u0, int &pi)->int{
                // return 1 if unique pair (u0,pi) found; 2 if u0==x and unique pi found; 0 otherwise
                // Build candidate pairs
                vector<pair<int,int>> candPairs;
                for (int a = 1; a <= n; ++a) {
                    if (a == i || a == x) continue;
                    for (int b = 1; b <= n; ++b) {
                        if (b == i || b == x) continue;
                        bool ok = true;
                        for (int t = 0; t < nbits; ++t) {
                            int va = bits[t][a] ? 1 : 0;
                            int vb = bits[t][b] ? 1 : 0;
                            int diff = va - vb;
                            if (diff != delta[t]) { ok = false; break; }
                        }
                        if (ok) candPairs.emplace_back(a,b);
                    }
                }
                if (candPairs.size() == 1) {
                    u0 = candPairs[0].first;
                    pi = candPairs[0].second;
                    return 1;
                }
                if (candPairs.empty()) {
                    // try special case u0 == x: then delta[t] == - bits[t][pi]
                    int candidate_pi = -1, count_pi = 0;
                    for (int b = 1; b <= n; ++b) {
                        if (b == i || b == x) continue;
                        bool ok = true;
                        for (int t = 0; t < nbits; ++t) {
                            int vb = bits[t][b] ? 1 : 0;
                            int expect = -vb;
                            if (delta[t] != expect) { ok = false; break; }
                        }
                        if (ok) {
                            candidate_pi = b;
                            count_pi++;
                            if (count_pi > 1) break;
                        }
                    }
                    if (count_pi == 1) {
                        u0 = x;
                        pi = candidate_pi;
                        return 2;
                    }
                }
                return 0;
            };
            
            int u0 = -1, pi = -1;
            int m_used = 0;
            for (;;) {
                if (m_used >= MAX_M) break;
                // generate next random bit for all v != i, x
                vector<char> bit_for_v(n+1, 0);
                for (int v = 1; v <= n; ++v) {
                    if (v == i || v == x) { bit_for_v[v] = 0; continue; }
                    bit_for_v[v] = (char)(rng() & 1);
                }
                bits.push_back(bit_for_v);
                
                // build and ask two queries
                vector<int> q0 = build_query(i, bit_for_v, 0);
                int ans0 = ask(q0);
                vector<int> q1 = build_query(i, bit_for_v, 1);
                int ans1 = ask(q1);
                delta.push_back(ans1 - ans0);
                m_used++;
                
                int status = try_decode(m_used, u0, pi);
                if (status == 1) {
                    // Found both u0 and p_i
                    mark_assign(i, pi);
                    if (p[u0] == 0) mark_assign(u0, i);
                    break;
                } else if (status == 2) {
                    // u0 == x, found p_i, and also p[x] = i
                    mark_assign(i, pi);
                    if (p[x] == 0) mark_assign(x, i);
                    break;
                }
                // else continue adding dimensions
            }
            // If still unresolved (should be very unlikely), fall back: attempt brute-force by adding more bits up to a safe cap
            if (p[i] == 0) {
                // add more dimensions deterministically if needed
                for (; m_used < 12 && p[i] == 0; ++m_used) {
                    vector<char> bit_for_v(n+1, 0);
                    // Deterministic pattern: bit based on (v * prime + i * 7 + m_used) parity
                    for (int v = 1; v <= n; ++v) {
                        if (v == i || v == x) continue;
                        unsigned val = (unsigned)(v * 911382323u + (i * 7 + m_used) * 972663749u);
                        bit_for_v[v] = (char)((val >> 1) & 1);
                    }
                    bits.push_back(bit_for_v);
                    vector<int> q0 = build_query(i, bit_for_v, 0);
                    int ans0 = ask(q0);
                    vector<int> q1 = build_query(i, bit_for_v, 1);
                    int ans1 = ask(q1);
                    delta.push_back(ans1 - ans0);
                    
                    int status = 0;
                    int uu=-1, vv=-1;
                    auto tmp_bits = bits; // alias
                    auto tmp_delta = delta;
                    auto try_dec = [&](int nbits, int &uout, int &pout)->int{
                        vector<pair<int,int>> candPairs;
                        for (int a = 1; a <= n; ++a) {
                            if (a == i || a == x) continue;
                            for (int b = 1; b <= n; ++b) {
                                if (b == i || b == x) continue;
                                bool ok = true;
                                for (int t = 0; t < nbits; ++t) {
                                    int va = tmp_bits[t][a] ? 1 : 0;
                                    int vb = tmp_bits[t][b] ? 1 : 0;
                                    int diff = va - vb;
                                    if (diff != tmp_delta[t]) { ok = false; break; }
                                }
                                if (ok) candPairs.emplace_back(a,b);
                            }
                        }
                        if (candPairs.size() == 1) {
                            uout = candPairs[0].first;
                            pout = candPairs[0].second;
                            return 1;
                        }
                        if (candPairs.empty()) {
                            int candidate_pi = -1, count_pi = 0;
                            for (int b = 1; b <= n; ++b) {
                                if (b == i || b == x) continue;
                                bool ok = true;
                                for (int t = 0; t < nbits; ++t) {
                                    int vb = tmp_bits[t][b] ? 1 : 0;
                                    int expect = -vb;
                                    if (tmp_delta[t] != expect) { ok = false; break; }
                                }
                                if (ok) {
                                    candidate_pi = b;
                                    count_pi++;
                                    if (count_pi > 1) break;
                                }
                            }
                            if (count_pi == 1) {
                                uout = x;
                                pout = candidate_pi;
                                return 2;
                            }
                        }
                        return 0;
                    };
                    status = try_dec(m_used+1, uu, vv);
                    if (status == 1) {
                        mark_assign(i, vv);
                        if (p[uu] == 0) mark_assign(uu, i);
                        break;
                    } else if (status == 2) {
                        mark_assign(i, vv);
                        if (p[x] == 0) mark_assign(x, i);
                        break;
                    }
                }
                // As a last resort, if still not assigned due to pathological collision, assign by elimination later
                if (p[i] == 0) {
                    // do nothing here; we'll fill remaining by elimination at the end
                    // but to ensure progress, mark we won't loop infinitely
                    // break condition handled by assigned counter
                    // Continue to next i
                    // However to avoid stalling, attempt a final disambiguation:
                    // Try single candidate b by elimination of used values
                    vector<int> remainingVals;
                    for (int v = 1; v <= n; ++v) if (!used_val[v] && v != i) remainingVals.push_back(v);
                    if (remainingVals.size() == 1) {
                        mark_assign(i, remainingVals[0]);
                    }
                }
            }
        }
        
        // Fill any remaining unassigned by elimination (should be at most 0 or few)
        vector<int> remVals;
        for (int v = 1; v <= n; ++v) if (!used_val[v]) remVals.push_back(v);
        vector<int> remIdx;
        for (int i = 1; i <= n; ++i) if (p[i] == 0) remIdx.push_back(i);
        // Since it's a permutation, remIdx and remVals should be same size. Additionally, ensure p[i] != i.
        // We'll resolve cycles to avoid fixed points: simple method since n small, try all permutations of remVals (factorial might blow up if many).
        // But typically size is <= 2; still handle general with greedy swap if conflict.
        // First assign default mapping one-to-one
        int m = remIdx.size();
        for (int j = 0; j < m; ++j) {
            p[remIdx[j]] = remVals[j];
        }
        // Fix any fixed points among these by swapping
        // If any p[i]==i, swap its value with another j
        vector<int> bad;
        for (int j = 0; j < m; ++j) if (remIdx[j] == remVals[j]) bad.push_back(j);
        if (bad.size() == 1 && m >= 2) {
            int j = bad[0];
            int kidx = (j == 0 ? 1 : 0);
            swap(p[remIdx[j]], p[remIdx[kidx]]);
        } else if (bad.size() >= 2) {
            // rotate the values among bad indices
            vector<int> tmp;
            for (int idx: bad) tmp.push_back(remVals[idx]);
            rotate(tmp.begin(), tmp.begin()+1, tmp.end());
            int tcur = 0;
            for (int idxpos = 0; idxpos < (int)bad.size(); ++idxpos) {
                int j = bad[idxpos];
                p[remIdx[j]] = tmp[tcur++];
            }
        }
        
        cout << "!";
        for (int i = 1; i <= n; ++i) {
            cout << " " << p[i];
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}