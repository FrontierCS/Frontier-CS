#include <bits/stdc++.h>
using namespace std;

int main() {
  int b, w, x, y;
  cin >> b >> w >> x >> y;
  long long cost1 = LLONG_MAX / 2;
  vector<string> grid1;
  int r1 = 0, c1 = 0;
  bool possible1 = (b <= w + 1);
  if (possible1) {
    int num_main = b;
    int num_other = w;
    int sep = b - 1;
    int extra = w - sep;
    int cc = (extra == 0 ? 1 : (extra == 1 ? 2 : 2 * extra - 1));
    int hh;
    if (extra == 0) {
      hh = num_main + sep;
    } else {
      hh = num_main + 2 + sep;
    }
    long long totalt = (long long)hh * cc;
    if (totalt <= 100000 && totalt > 0) {
      long long num_b = totalt - ((long long)sep * cc + extra);
      long long num_wh = (long long)sep * cc + extra;
      cost1 = (long long)x * num_b + (long long)y * num_wh;
      char main_char = '@';
      char other_char = '.';
      vector<string> g;
      int embedding_block = num_main - 1;
      bool has_emb = (extra > 0);
      for (int blk = 0; blk < num_main; blk++) {
        int hgt = 1;
        bool emb = has_emb && (blk == embedding_block);
        if (emb) hgt = 3;
        for (int rh = 0; rh < hgt; rh++) {
          string row(cc, main_char);
          if (emb && rh == 1) {
            string mid(cc, main_char);
            int pos = 0;
            for (int i = 0; i < extra; i++) {
              if (pos < cc) {
                mid[pos] = other_char;
                pos += 2;
              }
            }
            row = mid;
          }
          g.push_back(row);
        }
        if (blk < num_main - 1) {
          string srow(cc, other_char);
          g.push_back(srow);
        }
      }
      r1 = g.size();
      c1 = cc;
      grid1 = g;
    }
  }
  long long cost2 = LLONG_MAX / 2;
  vector<string> grid2;
  int r2 = 0, c2 = 0;
  bool possible2 = (w <= b + 1);
  if (possible2) {
    int num_main = w;
    int num_other = b;
    int sep = w - 1;
    int extra = b - sep;
    int cc = (extra == 0 ? 1 : (extra == 1 ? 2 : 2 * extra - 1));
    int hh;
    if (extra == 0) {
      hh = num_main + sep;
    } else {
      hh = num_main + 2 + sep;
    }
    long long totalt = (long long)hh * cc;
    if (totalt <= 100000 && totalt > 0) {
      long long num_other_t = (long long)sep * cc + extra;
      long long num_main_t = totalt - num_other_t;
      cost2 = (long long)x * num_other_t + (long long)y * num_main_t;
      char main_char = '.';
      char other_char = '@';
      vector<string> g;
      int embedding_block = num_main - 1;
      bool has_emb = (extra > 0);
      for (int blk = 0; blk < num_main; blk++) {
        int hgt = 1;
        bool emb = has_emb && (blk == embedding_block);
        if (emb) hgt = 3;
        for (int rh = 0; rh < hgt; rh++) {
          string row(cc, main_char);
          if (emb && rh == 1) {
            string mid(cc, main_char);
            int pos = 0;
            for (int i = 0; i < extra; i++) {
              if (pos < cc) {
                mid[pos] = other_char;
                pos += 2;
              }
            }
            row = mid;
          }
          g.push_back(row);
        }
        if (blk < num_main - 1) {
          string srow(cc, other_char);
          g.push_back(srow);
        }
      }
      r2 = g.size();
      c2 = cc;
      grid2 = g;
    }
  }
  if (cost1 < cost2 || !possible2) {
    cout << r1 << " " << c1 << endl;
    for (auto& s : grid1) {
      cout << s << endl;
    }
  } else {
    cout << r2 << " " << c2 << endl;
    for (auto& s : grid2) {
      cout << s << endl;
    }
  }
  return 0;
}