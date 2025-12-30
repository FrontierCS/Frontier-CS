#include <bits/stdc++.h>
using namespace std;

struct Point {
  int x, y, w;
};

bool cmp(const Point& a, const Point& b) {
  return a.x < b.x || (a.x == b.x && a.y < b.y);
}

struct Node {
  int total = 0, pref = 0, suf = 0, sub = 0, ts = 0;
};

const int MAXYY = 100000;
Node tree[4 * (MAXYY + 10)];
int cur_timee = 0;

Node get_effective(int idx, int ctimee) {
  if (tree[idx].ts == ctimee) return tree[idx];
  Node nn;
  return nn;
}

void update(int idx, int tl, int tr, int pos, int delta, int ctimee) {
  if (tree[idx].ts != ctimee) {
    tree[idx].total = 0;
    tree[idx].pref = 0;
    tree[idx].suf = 0;
    tree[idx].sub = 0;
    tree[idx].ts = ctimee;
  }
  if (tl == tr) {
    tree[idx].total += delta;
    tree[idx].pref = tree[idx].total;
    tree[idx].suf = tree[idx].total;
    tree[idx].sub = tree[idx].total;
    return;
  }
  int tm = (tl + tr) / 2;
  if (pos <= tm)
    update(2 * idx, tl, tm, pos, delta, ctimee);
  else
    update(2 * idx + 1, tm + 1, tr, pos, delta, ctimee);
  Node ln = get_effective(2 * idx, ctimee);
  Node rn = get_effective(2 * idx + 1, ctimee);
  tree[idx].total = ln.total + rn.total;
  tree[idx].pref = max(ln.pref, ln.total + rn.pref);
  tree[idx].suf = max(rn.suf, rn.total + ln.suf);
  tree[idx].sub = max({ln.sub, rn.sub, ln.suf + rn.pref});
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N;
  cin >> N;
  vector<Point> PP(2 * N);
  for (int i = 0; i < 2 * N; i++) {
    int xx, yy;
    cin >> xx >> yy;
    PP[i].x = xx;
    PP[i].y = yy;
    PP[i].w = (i < N ? 1 : -1);
  }
  sort(PP.begin(), PP.end(), cmp);
  int mm = 2 * N;
  int best_sc = 1;
  int best_xl = 0, best_xr = 0, best_yb = 0, best_yt = 0;
  bool has_good = false;
  cur_timee = 0;
  for (int l = 0; l < mm; l++) {
    cur_timee++;
    for (int r = l; r < mm; r++) {
      update(1, 0, MAXYY, PP[r].y, PP[r].w, cur_timee);
      int ab = tree[1].sub;
      int sc = max(0, ab + 1);
      if (sc > best_sc && ab >= 1) {
        vector<pair<int, int>> active;
        for (int ii = l; ii <= r; ii++) {
          active.emplace_back(PP[ii].y, PP[ii].w);
        }
        int kk = active.size();
        if (kk == 0) continue;
        sort(active.begin(), active.end());
        int max_ending_here = active[0].second;
        int max_so_far = active[0].second;
        int curr_start = 0;
        int best_startt = 0;
        int best_endd = 0;
        for (int i = 1; i < kk; i++) {
          int new_end = max_ending_here + active[i].second;
          if (new_end > active[i].second) {
            max_ending_here = new_end;
          } else {
            max_ending_here = active[i].second;
            curr_start = i;
          }
          if (max_ending_here > max_so_far) {
            max_so_far = max_ending_here;
            best_startt = curr_start;
            best_endd = i;
          }
        }
        if (max_so_far >= 1) {
          best_sc = sc;
          best_xl = PP[l].x;
          best_xr = PP[r].x;
          best_yb = active[best_startt].first;
          best_yt = active[best_endd].first;
          has_good = true;
        }
      }
    }
  }
  vector<pair<int, int>> verts;
  if (has_good) {
    int xl = best_xl, xr = best_xr, yb = best_yb, yt = best_yt;
    bool degen_x = (xl == xr);
    bool degen_y = (yb == yt);
    bool fixed = false;
    if (degen_x && !degen_y) {
      if (xl > 0) {
        bool extra = false;
        for (auto& p : PP) {
          if (p.x == xl - 1 && p.y >= yb && p.y <= yt) {
            extra = true;
            break;
          }
        }
        if (!extra) {
          xl--;
          fixed = true;
        }
      }
      if (!fixed && xr < 100000) {
        bool extra = false;
        for (auto& p : PP) {
          if (p.x == xr + 1 && p.y >= yb && p.y <= yt) {
            extra = true;
            break;
          }
        }
        if (!extra) {
          xr++;
          fixed = true;
        }
      }
    } else if (degen_y && !degen_x) {
      if (yb > 0) {
        bool extra = false;
        for (auto& p : PP) {
          if (p.y == yb - 1 && p.x >= xl && p.x <= xr) {
            extra = true;
            break;
          }
        }
        if (!extra) {
          yb--;
          fixed = true;
        }
      }
      if (!fixed && yt < 100000) {
        bool extra = false;
        for (auto& p : PP) {
          if (p.y == yt + 1 && p.x >= xl && p.x <= xr) {
            extra = true;
            break;
          }
        }
        if (!extra) {
          yt++;
          fixed = true;
        }
      }
    }
    if (fixed || (!degen_x && !degen_y)) {
      verts = {{xl, yb}, {xr, yb}, {xr, yt}, {xl, yt}};
    } else {
      has_good = false;
    }
  }
  if (verts.empty()) {
    int px = -1, py = -1;
    for (auto& p : PP) {
      if (p.w == 1) {
        px = p.x;
        py = p.y;
        break;
      }
    }
    vector<vector<pair<int, int>>> dirs = {
        {{px + 1, py}, {px + 1, py + 1}, {px, py + 1}},
        {{px - 1, py}, {px - 1, py + 1}, {px, py + 1}},
        {{px + 1, py}, {px + 1, py - 1}, {px, py - 1}},
        {{px - 1, py}, {px - 1, py - 1}, {px, py - 1}}};
    set<pair<int, int>> allp;
    for (auto& p : PP) allp.insert({p.x, p.y});
    bool ffound = false;
    vector<pair<int, int>> chverts;
    for (auto& cd : dirs) {
      bool okk = true;
      for (auto pr : cd) {
        int a = pr.first, b = pr.second;
        if (a < 0 || a > 100000 || b < 0 || b > 100000 || allp.count({a, b})) {
          okk = false;
          break;
        }
      }
      if (okk) {
        chverts = {{px, py}, cd[0], cd[1], cd[2]};
        ffound = true;
        break;
      }
    }
    verts = chverts;
  }
  cout << 4 << '\n';
  for (auto [a, b] : verts) {
    cout << a << " " << b << '\n';
  }
  return 0;
}