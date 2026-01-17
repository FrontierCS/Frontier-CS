#include <bits/stdc++.h>
using namespace std;

int main() {
  int b, w, x, y;
  cin >> b >> w >> x >> y;
  auto build = [&](char slab_ch, char sep_ch, int num_s, int ss, int ee) -> pair<vector<string>, long long> {
    if (num_s == 0) return {{}, 0LL};
    vector<int> ms(num_s, ee / num_s);
    int rem = ee % num_s;
    for (int i = 0; i < rem; i++) ms[i]++;
    vector<int> hs(num_s);
    vector<int> req_cs(num_s, 0);
    int max_c = 0;
    for (int j = 0; j < num_s; j++) {
      int mm = ms[j];
      bool is_f = (j == 0);
      bool is_l = (j == num_s - 1);
      if (mm == 0) {
        hs[j] = 1;
        req_cs[j] = 1;
      } else {
        int this_h;
        int this_c;
        if (ss == 0) {
          if (mm <= 2) {
            this_h = 1;
            this_c = mm + 1;
          } else {
            this_h = 2;
            this_c = 2 * mm - 1;
          }
        } else {
          bool can_h2 = is_f || is_l;
          if (mm <= 2 && can_h2) {
            this_h = 2;
            this_c = mm + 1;
          } else {
            this_h = 3;
            this_c = (mm <= 2 ? mm + 1 : 2 * mm - 1);
          }
        }
        hs[j] = this_h;
        req_cs[j] = this_c;
      }
      max_c = max(max_c, req_cs[j]);
    }
    int cc = max(1, max_c);
    vector<string> g;
    for (int j = 0; j < num_s; j++) {
      int hh = hs[j];
      int mm = ms[j];
      bool is_f = (j == 0);
      bool is_l = (j == num_s - 1);
      int hole_r_local;
      if (hh == 1) {
        hole_r_local = 0;
      } else if (ss == 0 && hh == 2) {
        hole_r_local = 0;
      } else if (is_f && hh == 2) {
        hole_r_local = 0;
      } else if (is_l && hh == 2) {
        hole_r_local = hh - 1;
      } else {
        hole_r_local = 1;
      }
      vector<string> slab_r(hh, string(cc, slab_ch));
      if (mm > 0) {
        string& hl = slab_r[hole_r_local];
        if (mm == 1) {
          hl[0] = sep_ch;
        } else if (mm == 2) {
          hl[0] = sep_ch;
          hl[cc - 1] = sep_ch;
        } else {
          int patw = 2 * mm - 1;
          for (int p = 0; p < patw; p++) {
            if (p % 2 == 0) hl[p] = sep_ch;
          }
        }
      }
      for (string& str : slab_r) g.push_back(str);
      if (j < num_s - 1) {
        g.push_back(string(cc, sep_ch));
      }
    }
    int rr = g.size();
    long long nblack = 0;
    for (string& str : g) {
      for (char ch : str) {
        if (ch == '@') nblack++;
      }
    }
    long long nwhite = (long long)rr * cc - nblack;
    long long tcost = nblack * (long long)x + nwhite * (long long)y;
    return {g, tcost};
  };
  vector<string> chosen_g;
  long long min_cost = LLONG_MAX / 2;
  bool can_black = (b >= 1 && b - 1 <= w);
  bool can_white = (w >= 1 && w - 1 <= b);
  if (can_black) {
    int ss = b - 1;
    int ee = w - ss;
    auto cand = build('@', '.', b, ss, ee);
    int rrr = cand.first.size();
    int ccc = (rrr == 0 ? 0 : cand.first[0].size());
    if ((long long)rrr * ccc <= 100000) {
      min_cost = cand.second;
      chosen_g = cand.first;
    }
  }
  if (can_white) {
    int ss = w - 1;
    int ee = b - ss;
    auto cand = build('.', '@', w, ss, ee);
    int rrr = cand.first.size();
    int ccc = (rrr == 0 ? 0 : cand.first[0].size());
    if ((long long)rrr * ccc <= 100000) {
      long long ccost = cand.second;
      if (ccost < min_cost) {
        min_cost = ccost;
        chosen_g = cand.first;
      }
    }
  }
  int rr = chosen_g.size();
  int cc = (rr == 0 ? 1 : chosen_g[0].size());
  cout << rr << " " << cc << endl;
  for (string& str : chosen_g) {
    cout << str << endl;
  }
  return 0;
}