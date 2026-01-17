#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

struct Instr {
  bool is_halt;
  int a, x, b, y;
};

vector<Instr> code;
int current_pos;

struct Block {
  int start, last;
};

pair<int, int> generate_G(int i, int cont_pos) {
  int start_pos = current_pos;
  if (i == 0) {
    int p1 = current_pos++;
    code.resize(p1);
    code[p1 - 1] = {false, 1024, 1, 1, 0}; // y temp 0
    int p2 = current_pos++;
    code.resize(p2);
    code[p2 - 1] = {false, 1, cont_pos, 1024, 1};
    code[p1 - 1].y = p2;
    return {p1, p2};
  } else {
    int marker = 10 + i;
    int tempv = 100 + i;
    int push_pos = current_pos++;
    code.resize(push_pos);
    code[push_pos - 1] = {false, 1024, 1, marker, 0};
    auto inner = generate_G(i - 1, 0);
    int inner_s = inner.first;
    int inner_l = inner.second;
    int checker_pos = current_pos++;
    code.resize(checker_pos);
    code[checker_pos - 1] = {false, marker, inner_s, tempv, current_pos};
    int ptemp_pos = current_pos++;
    code.resize(ptemp_pos);
    code[ptemp_pos - 1] = {false, tempv, cont_pos, 1024, 1};
    code[push_pos - 1].y = inner_s;
    code[inner_l - 1].x = checker_pos;
    return {push_pos, ptemp_pos};
  }
}

int main() {
  ll k;
  cin >> k;
  if (k == 1) {
    cout << 1 << endl;
    cout << "HALT PUSH 1 GOTO 1" << endl;
    return 0;
  }
  ll ss[31];
  ss[0] = 2;
  for (int i = 1; i <= 30; i++) ss[i] = 2 * ss[i - 1] + 4;
  vector<int> selected;
  ll rem = k - 1;
  for (int i = 30; i >= 0; i--) {
    if (ss[i] <= rem) {
      selected.push_back(i);
      rem -= ss[i];
    }
  }
  int numb = rem / 2;
  for (int j = 0; j < numb; j++) selected.push_back(0);
  code.clear();
  current_pos = 1;
  vector<Block> blocks;
  for (size_t si = 0; si < selected.size(); si++) {
    int ii = selected[si];
    auto p = generate_G(ii, 0);
    blocks.push_back({p.first, p.second});
  }
  int temp_n = current_pos - 1;
  int halt_pos = current_pos;
  code.resize(halt_pos);
  code[halt_pos - 1] = {true, 0, 0, 99, temp_n};
  current_pos++;
  int n = current_pos - 1;
  code[halt_pos - 1].y = n;
  if (!blocks.empty()) {
    code[blocks.back().last - 1].x = halt_pos;
    for (size_t jj = blocks.size() - 2;; jj--) {
      if (jj == size_t(-1)) break;
      code[blocks[jj].last - 1].x = blocks[jj + 1].start;
    }
  }
  cout << n << endl;
  for (int p = 1; p <= n; p++) {
    Instr ins = code[p - 1];
    if (ins.is_halt) {
      cout << "HALT PUSH " << ins.b << " GOTO " << ins.y;
    } else {
      cout << "POP " << ins.a << " GOTO " << ins.x << " PUSH " << ins.b << " GOTO " << ins.y;
    }
    cout << endl;
  }
  return 0;
}