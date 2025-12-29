#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

vector<ll> full_S;
int m_global;
ll total_C_global;

ll query_vec(const vector<ll>& qv) {
  if (qv.empty()) return 0;
  cout << 0 << " " << qv.size();
  for (ll x : qv) cout << " " << x;
  cout << endl;
  cout.flush();
  ll res;
  cin >> res;
  return res;
}

void guess(ll n) {
  cout << 1 << " " << n << endl;
  cout.flush();
  exit(0);
}

pair<int, int> find_colliding(const vector<int>& curr, const vector<ll>& S) {
  int sz = curr.size();
  if (sz == 2) {
    vector<ll> qv = {S[curr[0]], S[curr[1]]};
    ll cc = query_vec(qv);
    if (cc == 1) return {curr[0], curr[1]};
    assert(false);
  }
  int half = sz / 2;
  vector<int> left(curr.begin(), curr.begin() + half);
  vector<int> right(curr.begin() + half, curr.end());
  vector<ll> qleft, qright;
  for (int i : left) qleft.push_back(S[i]);
  for (int i : right) qright.push_back(S[i]);
  ll cl = query_vec(qleft);
  ll cr = query_vec(qright);
  if (cl > 0) {
    return find_colliding(left, S);
  } else if (cr > 0) {
    return find_colliding(right, S);
  } else {
    // cross
    vector<int> fixed = left;
    vector<int> searchh = right;
    if (left.size() > right.size()) {
      fixed = right;
      searchh = left;
    }
    // binary search to find one in searchh
    int l = 0, h = searchh.size() - 1;
    while (l < h) {
      int md = l + (h - l) / 2;
      vector<int> test_group(searchh.begin() + l, searchh.begin() + md + 1);
      vector<ll> qf;
      for (int ii : fixed) qf.push_back(S[ii]);
      for (int ii : test_group) qf.push_back(S[ii]);
      ll ct = query_vec(qf);
      if (ct > 0) {
        h = md;
      } else {
        l = md + 1;
      }
    }
    int b_local = l;
    int b_idx = searchh[b_local];
    // now find a in fixed
    int l2 = 0, h2 = fixed.size() - 1;
    while (l2 < h2) {
      int md2 = l2 + (h2 - l2) / 2;
      vector<int> test_group2(fixed.begin() + l2, fixed.begin() + md2 + 1);
      vector<ll> qb = {S[b_idx]};
      for (int ii : test_group2) qb.push_back(S[ii]);
      ll ct2 = query_vec(qb);
      if (ct2 > 0) {
        h2 = md2;
      } else {
        l2 = md2 + 1;
      }
    }
    int a_local = l2;
    int a_idx = fixed[a_local];
    return {min(a_idx, b_idx), max(a_idx, b_idx)};
  }
}

vector<ll> get_divisors(ll num) {
  vector<ll> divs;
  for (ll i = 1; i * i <= num; ++i) {
    if (num % i == 0) {
      divs.push_back(i);
      if (i != num / i) divs.push_back(num / i);
    }
  }
  sort(divs.begin(), divs.end());
  return divs;
}

int main() {
  srand(time(0));
  // doubling for small n
  int max_log = 16;
  for (int k = 1; k <= max_log; ++k) {
    int mm = (1 << k);
    vector<ll> seq(mm);
    for (int i = 0; i < mm; ++i) seq[i] = i + 1;
    ll cc = query_vec(seq);
    if (cc > 0) {
      ll nn = (ll)mm - cc;
      guess(nn);
    }
  }
  // now n > 65536
  // birthday
  int m = 50000;
  ll base = 1LL << 50;
  ll range_size = 2000000000LL;
  mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
  vector<int> indices(m);
  for (int i = 0; i < m; ++i) indices[i] = i;
  bool found_query = false;
  vector<ll> S;
  ll total_C;
  for (int tryy = 0; tryy < 20; ++tryy) {
    set<ll> used_off;
    S.resize(m);
    for (int i = 0; i < m; ++i) {
      ll off;
      do {
        off = rng() % range_size;
      } while (used_off.count(off));
      used_off.insert(off);
      S[i] = base + off;
    }
    random_shuffle(indices.begin(), indices.end()); // random order
    total_C = query_vec(S);
    if (total_C > 0) {
      found_query = true;
      break;
    }
  }
  assert(found_query);
  full_S = S;
  total_C_global = total_C;
  m_global = m;
  pair<int, int> p = find_colliding(indices, S);
  ll d = abs(S[p.first] - S[p.second]);
  vector<ll> divs = get_divisors(d);
  for (ll c : divs) {
    if (c < 2 || c > 1000000000LL) continue;
    vector<ll> mods(m);
    for (int j = 0; j < m; ++j) {
      mods[j] = S[j] % c;
      if (mods[j] < 0) mods[j] += c; // in case negative
    }
    sort(mods.begin(), mods.end());
    ll sim_c = 0;
    int cnt = 1;
    for (int j = 1; j < m; ++j) {
      if (mods[j] == mods[j - 1]) {
        cnt++;
      } else {
        sim_c += (ll)cnt * (cnt - 1) / 2;
        cnt = 1;
      }
    }
    sim_c += (ll)cnt * (cnt - 1) / 2;
    if (sim_c == total_C) {
      guess(c);
    }
  }
  // if none, error
  assert(false);
  return 0;
}