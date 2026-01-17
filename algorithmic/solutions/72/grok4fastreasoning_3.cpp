#include <bits/stdc++.h>
using namespace std;
using ll = long long;

struct Vehicle {
    int id, len, fixed;
    bool horz;
};

ll get_hash(const vector<int>& ps, int base = 7) {
    ll h = 0;
    for (int p : ps) h = h * base + p;
    return h;
}

vector<int> get_pos(ll h, int nn, int base = 7) {
    vector<int> ps(nn);
    for (int i = nn - 1; i >= 0; i--) {
        ps[i] = h % base;
        h /= base;
    }
    return ps;
}

int solve_dist(vector<int> startp, const vector<Vehicle>& vehh, int nn, int ridx) {
    ll sh = get_hash(startp);
    if (startp[ridx] >= 6) return 0;
    queue<ll> q;
    unordered_map<ll, int> sdist;
    q.push(sh);
    sdist[sh] = 0;
    while (!q.empty()) {
        ll chh = q.front(); q.pop();
        int cdd = sdist[chh];
        vector<int> poss = get_pos(chh, nn);
        if (poss[ridx] >= 6) return cdd;
        bool occc[6][6];
        memset(occc, 0, sizeof(occc));
        for (int vii = 0; vii < nn; vii++) {
            int pp = poss[vii];
            bool hho = vehh[vii].horz;
            int ff = vehh[vii].fixed;
            int lee = vehh[vii].len;
            if (hho) {
                int rr = ff;
                for (int kk = 0; kk < lee; kk++) {
                    int cc = pp + kk;
                    if (cc >= 0 && cc < 6) occc[rr][cc] = true;
                }
            } else {
                int cc = ff;
                for (int kk = 0; kk < lee; kk++) {
                    int rr = pp + kk;
                    if (rr >= 0 && rr < 6) occc[rr][cc] = true;
                }
            }
        }
        for (int vii = 0; vii < nn; vii++) {
            bool isrr = (vehh[vii].id == 1);
            bool hho = vehh[vii].horz;
            int ff = vehh[vii].fixed;
            int lee = vehh[vii].len;
            int pp = poss[vii];
            for (int ddirr = 0; ddirr < 2; ddirr++) {
                int deltaa = (ddirr ? 1 : -1);
                int brr, bcc;
                if (hho) {
                    if (deltaa == 1) {
                        bcc = pp + lee;
                        brr = ff;
                    } else {
                        bcc = pp - 1;
                        brr = ff;
                    }
                } else {
                    if (deltaa == 1) {
                        brr = pp + lee;
                        bcc = ff;
                    } else {
                        brr = pp - 1;
                        bcc = ff;
                    }
                }
                bool bboardd = (brr >= 0 && brr < 6 && bcc >= 0 && bcc < 6);
                bool emptybb = !bboardd || !occc[brr][bcc];
                bool alllow = bboardd ? emptybb : (isrr && hho && deltaa == 1 && ff == 2);
                if (alllow) {
                    int npp = pp + deltaa;
                    bool rangeokk = true;
                    if (!isrr) {
                        int endpp = npp + lee - 1;
                        if (npp < 0 || endpp > 5) rangeokk = false;
                    } else {
                        if (npp < 0 || npp > 6) rangeokk = false;
                    }
                    if (rangeokk) {
                        vector<int> npps = poss;
                        npps[vii] = npp;
                        ll nhh = get_hash(npps);
                        if (sdist.count(nhh) == 0) {
                            sdist[nhh] = cdd + 1;
                            q.push(nhh);
                        }
                    }
                }
            }
        }
    }
    return -1;
}

int main() {
    int g[6][6];
    for (int i = 0; i < 6; i++) for (int j = 0; j < 6; j++) cin >> g[i][j];
    map<int, vector<pair<int, int>>> partss;
    int maxidd = 0;
    for (int i = 0; i < 6; i++) for (int j = 0; j < 6; j++) if (g[i][j]) {
        partss[g[i][j]].emplace_back(i, j);
        maxidd = max(maxidd, g[i][j]);
    }
    int nn = maxidd;
    vector<Vehicle> vehh(nn);
    vector<int> init_pos(nn);
    for (int idd = 1; idd <= nn; idd++) {
        auto& pss = partss[idd];
        if (pss.empty()) continue;
        int r00 = pss[0].first, c00 = pss[0].second;
        int minrr = r00, maxrr = r00, mincc = c00, maxcc = c00;
        bool allhh = true, allvv = true;
        for (auto [rr, cc] : pss) {
            minrr = min(minrr, rr); maxrr = max(maxrr, rr);
            mincc = min(mincc, cc); maxcc = max(maxcc, cc);
            if (rr != r00) allhh = false;
            if (cc != c00) allvv = false;
        }
        int lenn = pss.size();
        bool horzz;
        int fixedd;
        int curposs;
        if (allhh && (maxcc - mincc + 1 == lenn)) {
            horzz = true;
            fixedd = r00;
            curposs = mincc;
        } else if (allvv && (maxrr - minrr + 1 == lenn)) {
            horzz = false;
            fixedd = c00;
            curposs = minrr;
        } else {
            assert(false);
        }
        vehh[idd - 1] = {idd, lenn, fixedd, horzz};
        init_pos[idd - 1] = curposs;
    }
    int ridx = 0;
    ll ihh = get_hash(init_pos);
    queue<ll> fq;
    unordered_map<ll, int> form_dist;
    unordered_map<ll, pair<ll, pair<int, char>>> parentt;
    fq.push(ihh);
    form_dist[ihh] = 0;
    vector<pair<int, ll>> bestt(7, {INT_MAX / 2, -1LL});
    vector<int> i_pos = init_pos;
    int init_rp = i_pos[0];
    bestt[init_rp] = {0, ihh};
    while (!fq.empty()) {
        ll ch = fq.front(); fq.pop();
        int cd = form_dist[ch];
        vector<int> pos = get_pos(ch, nn);
        int rp = pos[0];
        if (cd < bestt[rp].first) {
            bestt[rp] = {cd, ch};
        }
        bool occ[6][6];
        memset(occ, 0, sizeof(occ));
        for (int vi = 0; vi < nn; vi++) {
            int p = pos[vi];
            bool ho = vehh[vi].horz;
            int f = vehh[vi].fixed;
            int le = vehh[vi].len;
            if (ho) {
                int r = f;
                for (int k = 0; k < le; k++) {
                    int c = p + k;
                    if (c >= 0 && c < 6) occ[r][c] = true;
                }
            } else {
                int c = f;
                for (int k = 0; k < le; k++) {
                    int r = p + k;
                    if (r >= 0 && r < 6) occ[r][c] = true;
                }
            }
        }
        for (int vi = 0; vi < nn; vi++) {
            bool isr = (vehh[vi].id == 1);
            bool ho = vehh[vi].horz;
            int f = vehh[vi].fixed;
            int le = vehh[vi].len;
            int p = pos[vi];
            for (int ddir = 0; ddir < 2; ddir++) {
                int delta = (ddir ? 1 : -1);
                int br, bc;
                if (ho) {
                    if (delta == 1) {
                        bc = p + le;
                        br = f;
                    } else {
                        bc = p - 1;
                        br = f;
                    }
                } else {
                    if (delta == 1) {
                        br = p + le;
                        bc = f;
                    } else {
                        br = p - 1;
                        bc = f;
                    }
                }
                bool bboard = (br >= 0 && br < 6 && bc >= 0 && bc < 6);
                bool emptyb = !bboard || !occ[br][bc];
                bool allow = bboard ? emptyb : (isr && ho && delta == 1 && f == 2);
                if (allow) {
                    int np = p + delta;
                    bool rangeok = true;
                    if (!isr) {
                        int endp = np + le - 1;
                        if (np < 0 || endp > 5) rangeok = false;
                    } else {
                        if (np < 0 || np > 6) rangeok = false;
                    }
                    if (rangeok) {
                        vector<int> nps = pos;
                        nps[vi] = np;
                        ll nh = get_hash(nps);
                        if (form_dist.count(nh) == 0) {
                            form_dist[nh] = cd + 1;
                            fq.push(nh);
                            int vehid = vehh[vi].id;
                            char dirc;
                            if (ho) {
                                dirc = (delta == 1 ? 'R' : 'L');
                            } else {
                                dirc = (delta == 1 ? 'D' : 'U');
                            }
                            parentt[nh] = {ch, {vehid, dirc}};
                        }
                    }
                }
            }
        }
    }
    int min_rpp = 7;
    for (int k = 0; k < 7; k++) {
        if (bestt[k].first < INT_MAX / 2) {
            min_rpp = k;
            break;
        }
    }
    assert(min_rpp < 7);
    ll besthh = bestt[min_rpp].second;
    int formm_stepss = bestt[min_rpp].first;
    int your_stepss = solve_dist(get_pos(besthh, nn), vehh, nn, ridx);
    cout << your_stepss << " " << formm_stepss << endl;
    if (formm_stepss > 0) {
        vector<string> mlistt;
        ll curr = besthh;
        while (curr != ihh) {
            auto pr = parentt[curr];
            ll preev = pr.first;
            int viid = pr.second.first;
            char dd = pr.second.second;
            mlistt.push_back(to_string(viid) + " " + dd);
            curr = preev;
        }
        reverse(mlistt.begin(), mlistt.end());
        for (string s : mlistt) {
            cout << s << endl;
        }
    }
    return 0;
}