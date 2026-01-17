#include <bits/stdc++.h>
using namespace std;

vector<int> get_ds(long long t) {
  if (t == 0) return {};
  if (t < 0 || t % 2 != 0) return {-1};
  // try d=2
  vector<int> res_two;
  if (t >= 6 && (t - 6) % 2 == 0) {
    long long sub = (t - 6) / 2;
    auto sub_ds = get_ds(sub);
    bool success = sub_ds.empty() || (!sub_ds.empty() && sub_ds[0] != -1);
    if (success) {
      res_two = {2};
      res_two.insert(res_two.end(), sub_ds.begin(), sub_ds.end());
      return res_two;
    }
  }
  // d=1
  long long sub = t - 2;
  if (sub < 0) return {-1};
  auto sub_ds = get_ds(sub);
  bool success = sub_ds.empty() || (!sub_ds.empty() && sub_ds[0] != -1);
  if (!success) return {-1};
  vector<int> res = {1};
  res.insert(res.end(), sub_ds.begin(), sub_ds.end());
  return res;
}

int next_pos_global;
vector<string> pprog_global;
int n_global;
int halt_pos_global;

void build_level(int lev, int after_pos, const vector<int>& ds) {
  int m = ds.size();
  int dd = ds[m - 1 - lev];  // lev=0 outer ds[ m-1 -0 ]=ds.back() wait no.
  // Wait, to make lev=0 inner, we need ds reversed already.
  // Assume ds is reversed, ds[0] inner, ds[m-1] outer, lev from m-1 down to 0
  // Wait, let's adjust the call.
  // To avoid confusion, let's pass the current lev index from outer to inner, but since iterative? Wait, since recursive, let's make lev the index in reversed ds.
  // For simplicity, since small, but to match, let's reverse ds before calling.
  // In main, after getting ds_ = get_ds(tt);
  // vector<int> levels = ds_;
  // reverse(levels.begin(), levels.end()); // now levels[0] inner, levels[m-1] outer
  // then build_level(m-1, halt_pos_global, levels);
  // in function void build_level(int lev, int after_pos, const vector<int>& levels) {
  int dd = levels[lev];
  bool has_inner = (lev > 0);
  int l_start = next_pos_global++;
  int disp;
  if (dd == 1) {
    int p1 = next_pos_global++;
    disp = p1;
    if (has_inner) {
      int inner_start_temp = next_pos_global;
      build_level(lev - 1, disp, levels);
      int this_inner_start = inner_start_temp;
      pprog_global[l_start - 1] = "POP 100 GOTO " + to_string(after_pos) + " PUSH 1 GOTO " + to_string(this_inner_start);
      pprog_global[p1 - 1] = "POP 1 GOTO " + to_string(after_pos) + " PUSH 1024 GOTO " + to_string(after_pos);
    } else {
      int this_inner_start = p1;
      pprog_global[l_start - 1] = "POP 100 GOTO " + to_string(after_pos) + " PUSH 1 GOTO " + to_string(this_inner_start);
      pprog_global[p1 - 1] = "POP 1 GOTO " + to_string(after_pos) + " PUSH 1024 GOTO " + to_string(after_pos);
    }
  } else { // dd==2
    int push1p = next_pos_global++;
    int d_disp = next_pos_global++;
    int p3 = next_pos_global++;
    int p1 = next_pos_global++;
    disp = d_disp;
    int temp_inner = 0;
    if (has_inner) {
      int inner_start_temp = next_pos_global;
      build_level(lev - 1, disp, levels);
      temp_inner = inner_start_temp;
    } else {
      temp_inner = d_disp;
    }
    pprog_global[l_start - 1] = "POP 100 GOTO " + to_string(after_pos) + " PUSH 2 GOTO " + to_string(temp_inner);
    pprog_global[push1p -