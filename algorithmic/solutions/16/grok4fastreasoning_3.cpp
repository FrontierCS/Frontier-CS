#include <bits/stdc++.h>
using namespace std;

long long cycle_dist(long long a, long long b, long long n) {
    long long diff = abs(a - b);
    return min(diff, n - diff);
}

int get_vertex_cw(int s, int steps, int n) {
    return ((s - 1LL + steps) % n + n) % n + 1;
}

int get_vertex_ccw(int s, int steps, int n) {
    return ((s - 1LL - steps + 1LL * n * ((steps / n) + 1)) % n + n) % n + 1;
}

vector<pair<int, int>> get_intersect(int a1, int b1, int s1, int a2, int b2, int s2, int minx, int maxx, int miny, int maxy) {
    vector<pair<int, int>> res;
    for (int rx1 = 0; rx1 < 2; ++rx1) {
        int sx1 = (rx1 == 0 ? 1 : -1);
        for (int ry1 = 0; ry1 < 2; ++ry1) {
            int sy1 = (ry1 == 0 ? 1 : -1);
            long long rhs1 = s1 + 1LL * sx1 * a1 + 1LL * sy1 * b1;
            int cx1 = sx1, cy1 = sy1;
            for (int rx2 = 0; rx2 < 2; ++rx2) {
                int sx2 = (rx2 == 0 ? 1 : -1);
                for (int ry2 = 0; ry2 < 2; ++ry2) {
                    int sy2 = (ry2 == 0 ? 1 : -1);
                    long long rhs2 = s2 + 1LL * sx2 * a2 + 1LL * sy2 * b2;
                    int cx2 = sx2, cy2 = sy2;
                    long long det = 1LL * cx1 * cy2 - 1LL * cx2 * cy1;
                    if (det == 0) continue;
                    long long numx = rhs1 * 1LL * cy2 - rhs2 * 1LL * cy1;
                    long long numy = cx1 * 1LL * rhs2 - cx2 * 1LL * rhs1;
                    if (numx % det != 0 || numy % det != 0) continue;
                    long long xx = numx / det;
                    long long yy = numy / det;
                    if (xx < minx || xx > maxx || yy < miny || yy > maxy) continue;
                    bool ok1x = (rx1 == 0 ? (xx >= a1) : (xx < a1));
                    bool ok1y = (ry1 == 0 ? (yy >= b1) : (yy < b1));
                    bool ok2x = (rx2 == 0 ? (xx >= a2) : (xx < a2));
                    bool ok2y = (ry2 == 0 ? (yy >= b2) : (yy < b2));
                    if (ok1x && ok1y && ok2x && ok2y) {
                        long long sum1 = abs(xx - a1) + abs(yy - b1);
                        if (sum1 == s1) {
                            res.emplace_back(xx, yy);
                        }
                    }
                }
            }
        }
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        long long n;
        cin >> n;
        long long D = n / 2;
        vector<pair<long long, long long>> candidates;
        // Try from source 1, cw
        {
            long long lo = 1, hi = D + 1;
            while (lo < hi) {
                long long p = (lo + hi) / 2;
                long long y = get_vertex_cw(1, p, n);
                cout << "? 1 " << y << endl;
                cout.flush();
                long long dd;
                cin >> dd;
                if (dd < p) {
                    hi = p;
                } else {
                    lo = p + 1;
                }
            }
            long long pv = lo;
            if (pv <= D) {
                long long v = get_vertex_cw(1, pv, n);
                cout << "? 1 " << v << endl;
                cout.flush();
                long long d;
                cin >> d;
                long long pu = d - 1;
                long long uu;
                if (pu == 0) {
                    uu = 1;
                } else if (pu >= 1 && pu < pv) {
                    uu = get_vertex_cw(1, pu, n);
                } else {
                    pu = -1;
                }
                if (pu >= 0) {
                    long long cd = cycle_dist(uu, v, n);
                    if (cd >= 2) {
                        candidates.emplace_back(min(uu, v), max(uu, v));
                    }
                }
            }
        }
        // Try from source 1, ccw
        {
            long long lo = 1, hi = D + 1;
            while (lo < hi) {
                long long p = (lo + hi) / 2;
                long long y = get_vertex_ccw(1, p, n);
                cout << "? 1 " << y << endl;
                cout.flush();
                long long dd;
                cin >> dd;
                if (dd < p) {
                    hi = p;
                } else {
                    lo = p + 1;
                }
            }
            long long pv = lo;
            if (pv <= D) {
                long long v = get_vertex_ccw(1, pv, n);
                cout << "? 1 " << v << endl;
                cout.flush();
                long long d;
                cin >> d;
                long long pu = d - 1;
                long long uu;
                if (pu == 0) {
                    uu = 1;
                } else if (pu >= 1 && pu < pv) {
                    uu = get_vertex_ccw(1, pu, n);
                } else {
                    pu = -1;
                }
                if (pu >= 0) {
                    long long cd = cycle_dist(uu, v, n);
                    if (cd >= 2) {
                        candidates.emplace_back(min(uu, v), max(uu, v));
                    }
                }
            }
        }
        bool found = false;
        for (auto [u, v] : candidates) {
            cout << "? " << u << " " << v << endl;
            cout.flush();
            long long dd;
            cin >> dd;
            if (dd == 1) {
                cout << "! " << u << " " << v << endl;
                cout.flush();
                int r;
                cin >> r;
                if (r == 1) {
                    found = true;
                    break;
                } else {
                    // wrong, continue? but problem says exit
                    return 0;
                }
            }
        }
        if (found) continue;
        // across case
        long long Ls = 2, Le = n / 2;
        long long Rs = n / 2 + 2, Re = n;
        long long lenL = Le - Ls + 1;
        long long lenR = Re - Rs + 1;
        if (lenL <= 0 || lenR <= 0) {
            // impossible
            assert(false);
        }
        vector<long long> fs, gs;
        long long stepL = lenL / 4;
        fs.push_back(Ls + stepL);
        fs.push_back(Ls + 3 * stepL);
        long long stepR = lenR / 4;
        gs.push_back(Rs + stepR);
        gs.push_back(Rs + 3 * stepR);
        vector<tuple<long long, long long, long long>> eqs;
        vector<tuple<long long, long long, long long>> ges;
        for (auto f : fs) {
            for (auto g : gs) {
                long long ex = cycle_dist(f, g, n);
                cout << "? " << f << " " << g << endl;
                cout.flush();
                long long dd;
                cin >> dd;
                long long tt = ex - 1;
                long long aa = f - Ls + 1;
                long long bb = g - Rs + 1;
                if (dd < ex) {
                    long long ss = dd - 1;
                    eqs.emplace_back(aa, bb, ss);
                } else {
                    ges.emplace_back(aa, bb, tt);
                }
            }
        }
        // now process
        vector<pair<long long, long long>> across_cands;
        if (!eqs.empty()) {
            if (eqs.size() >= 2) {
                auto [a1, b1, s1] = eqs[0];
                auto [a2, b2, s2] = eqs[1];
                auto cands_pos = get_intersect(a1, b1, s1, a2, b2, s2, 1, lenL, 1, lenR);
                for (auto [px, py] : cands_pos) {
                    bool ok = true;
                    for (auto [aa, bb, ss] : eqs) {
                        if (abs(px - aa) + abs(py - bb) != ss) {
                            ok = false;
                            break;
                        }
                    }
                    if (!ok) continue;
                    for (auto [aa, bb, tt] : ges) {
                        if (abs(px - aa) + abs(py - bb) < tt) {
                            ok = false;
                            break;
                        }
                    }
                    if (ok) {
                        long long uu = Ls + px - 1;
                        long long vv = Rs + py - 1;
                        long long cd = cycle_dist(uu, vv, n);
                        if (cd >= 2) {
                            across_cands.emplace_back(uu, vv);
                        }
                    }
                }
            } else {
                // add one more
                long long f_mid = (Ls + Le) / 2;
                long long g_mid = (Rs + Re) / 2;
                long long ex = cycle_dist(f_mid, g_mid, n);
                cout << "? " << f_mid << " " << g_mid << endl;
                cout.flush();
                long long dd;
                cin >> dd;
                long long aa = f_mid - Ls + 1;
                long long bb = g_mid - Rs + 1;
                if (dd < ex) {
                    long long ss = dd - 1;
                    eqs.emplace_back(aa, bb, ss);
                    // now eqs.size()==2, process as above
                    auto [a1, b1, s1] = eqs[0];
                    auto [a2, b2, s2] = eqs[1];
                    auto cands_pos = get_intersect(a1, b1, s1, a2, b2, s2, 1, lenL, 1, lenR);
                    // same as above, add to across_cands
                    for (auto [px, py] : cands_pos) {
                        bool ok = true;
                        for (auto [aaa, bbb, sss] : eqs) {
                            if (abs(px - aaa) + abs(py - bbb) != sss) {
                                ok = false;
                                break;
                            }
                        }
                        if (!ok) continue;
                        for (auto [aaa, bbb, ttt] : ges) {
                            if (abs(px - aaa) + abs(py - bbb) < ttt) {
                                ok = false;
                                break;
                            }
                        }
                        if (ok) {
                            long long uu = Ls + px - 1;
                            long long vv = Rs + py - 1;
                            long long cd = cycle_dist(uu, vv, n);
                            if (cd >= 2) {
                                across_cands.emplace_back(uu, vv);
                            }
                        }
                    }
                } else {
                    ges.emplace_back(aa, bb, ex - 1);
                    // still only 1 eq, but for safety, since rare, assume found or handle
                    // for now, skip or error
                }
            }
        }
        // now add across_cands to candidates
        for (auto pr : across_cands) {
            candidates.emplace_back(pr);
        }
        // now try candidates
        found = false;
        set<pair<long long, long long>> tried;
        for (auto [u, v] : candidates) {
            if (u > v) swap(u, v);
            if (tried.count({u, v})) continue;
            tried.insert({u, v});
            cout << "? " << u << " " << v << endl;
            cout.flush();
            long long dd;
            cin >> dd;
            if (dd == 1) {
                cout << "! " << u << " " << v << endl;
                cout.flush();
                int r;
                cin >> r;
                if (r == 1) {
                    found = true;
                    break;
                } else {
                    return 0;
                }
            }
        }
        if (!found) {
            // should not happen
            assert(false);
        }
    }
    return 0;
}