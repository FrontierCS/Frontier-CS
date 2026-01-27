#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

static int64 n;
static int64 la = 1, lb = 1;
static map<int64, int64> mp; // start -> ub for b, piecewise-constant nonincreasing; keys include n+1 sentinel

static int ask(int64 x, int64 y) {
    if (x < 1) x = 1;
    if (y < 1) y = 1;
    if (x > n) x = n;
    if (y > n) y = n;
    cout << x << ' ' << y << endl;
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == 0) exit(0);
    return ans;
}

static map<int64, int64>::iterator splitPos(int64 pos) {
    if (pos <= 1) return mp.begin();
    if (pos >= n + 1) return mp.find(n + 1);
    auto it = prev(mp.upper_bound(pos));
    if (it->first == pos) return it;
    mp[pos] = it->second;
    return mp.find(pos);
}

static int64 getUbAt(int64 a) {
    auto it = prev(mp.upper_bound(a));
    return it->second;
}

static void updateLa(int64 newLa) {
    if (newLa <= la) return;
    if (newLa > n) newLa = n + 1;
    splitPos(newLa);
    auto it = mp.find(newLa);
    mp.erase(mp.begin(), it);
    la = newLa;
}

static void mergeAround(map<int64, int64>::iterator it) {
    if (it == mp.end()) return;

    if (it != mp.begin()) {
        auto prv = prev(it);
        if (prv->second == it->second) {
            mp.erase(it);
            it = prv;
        }
    }
    auto nxt = next(it);
    while (nxt != mp.end() && nxt->second == it->second) {
        nxt = mp.erase(nxt);
    }
}

static void suffixChMin(int64 x, int64 newUb) {
    if (x > n) return;
    if (newUb < 0) newUb = 0;
    if (newUb >= n) return; // no effect if ub cap is already <= n; still safe to ignore

    auto it = splitPos(x);
    auto cur = it;
    while (cur != mp.end() && cur->first <= n && cur->second > newUb) {
        cur->second = newUb;
        ++cur;
    }
    it = mp.find(x);
    if (it != mp.end()) mergeAround(it);
}

static int64 computeRa() {
    if (la > n) return n;
    auto it = mp.lower_bound(la);
    if (it == mp.end() || it->first != la) {
        splitPos(la);
        it = mp.lower_bound(la);
    }

    int64 ra = la - 1;
    while (it != mp.end()) {
        if (it->first == n + 1) break;
        int64 ub = min<int64>(it->second, n);
        auto nxt = next(it);
        int64 r = min<int64>(n, nxt->first - 1);
        if (ub < lb) break;
        ra = r;
        it = nxt;
    }
    return ra;
}

static void pruneAfter(int64 ra) {
    if (ra >= n) return;
    int64 cut = ra + 1;
    if (cut > n) cut = n + 1;
    splitPos(cut);
    auto itCut = mp.find(cut);
    auto itEnd = mp.find(n + 1);
    if (itCut == mp.end() || itEnd == mp.end()) return;
    auto it = next(itCut);
    if (it != itEnd) mp.erase(it, itEnd);
}

static void solveWithFixedA(int64 a) {
    int64 ub = min<int64>(getUbAt(a), n);
    int64 lo = lb, hi = ub;
    while (lo <= hi) {
        int64 mid = lo + (hi - lo) / 2;
        int ans = ask(a, mid);
        if (ans == 2) {
            lo = mid + 1;
            lb = max(lb, mid + 1);
        } else if (ans == 3) {
            hi = mid - 1;
        } else {
            exit(0);
        }
    }
    // If we ever get here, something went wrong with interaction consistency.
    // Try final guess:
    ask(a, lb);
}

static void solveWithFixedB(int64 b, int64 ra) {
    int64 lo = la, hi = ra;
    while (lo <= hi) {
        int64 mid = lo + (hi - lo) / 2;
        int ans = ask(mid, b);
        if (ans == 1) {
            lo = mid + 1;
            updateLa(mid + 1);
        } else if (ans == 3) {
            hi = mid - 1;
        } else {
            exit(0);
        }
        ra = min(ra, hi);
    }
    ask(la, b);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    mp.clear();
    mp[1] = n;
    mp[n + 1] = 0;

    la = 1;
    lb = 1;

    const int MAX_IT = 20000;
    for (int iters = 0; iters < MAX_IT; ++iters) {
        int64 ra = computeRa();
        pruneAfter(ra);

        if (la == ra) {
            solveWithFixedA(la);
            return 0;
        }

        int64 bMax = min<int64>(getUbAt(la), n);
        if (bMax == lb) {
            solveWithFixedB(lb, ra);
            return 0;
        }

        int64 x = la + (ra - la) / 2;
        int64 ubx = min<int64>(getUbAt(x), n);
        if (ubx < lb) {
            // Shouldn't happen if x in [la,ra], but just in case, push x left.
            x = la;
            ubx = min<int64>(getUbAt(x), n);
        }
        int64 y = lb + (ubx - lb) / 2;

        int ans = ask(x, y);
        if (ans == 1) {
            updateLa(x + 1);
        } else if (ans == 2) {
            lb = max(lb, y + 1);
        } else if (ans == 3) {
            suffixChMin(x, y - 1);
        } else {
            // ans==0 handled in ask()
            return 0;
        }
    }

    return 0;
}