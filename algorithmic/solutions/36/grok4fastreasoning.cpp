#include <bits/stdc++.h>
using namespace std;
using ll = long long;

mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
const ll MODD = 1000000000000000000LL;
const int KK = 35000;

ll queryy(const vector<ll>& vec) {
  if (vec.empty()) return 0;
  cout << 0 << " " << vec.size();
  for (ll x : vec) cout << " " << x;
  cout << endl;
  cout.flush();
  ll res;
  cin >> res;
  return res;
}

pair<ll, ll> find_coll(vector<ll> S) {
  int n = S.size();
  if (n <= 2) {
    return {S[0], S[1]};
  }
  int mid = n / 2;
  vector<ll> S1(S.begin(), S.begin() + mid);
  vector<ll> S2(S.begin() + mid, S.end());
  ll c1 = queryy(S1);
  ll c2 = queryy(S2);
  if (c1 >= 1) {
    return find_coll(S1);
  } else if (c2 >= 1) {
    return find_coll(S2);
  } else {
    vector<ll> curr1 = S1;
    while (curr1.size() > 1) {
      int m = curr1.size() / 2;
      vector<ll> left(curr1.begin(), curr1.begin() + m);
      vector<ll> testt;
      testt.reserve(left.size() + S2.size());
      testt.insert(testt.end(), left.begin(), left.end());
      testt.insert(testt.end(), S2.begin(), S2.end());
      ll cl = queryy(testt);
      if (cl >= 1) {
        curr1 = std::move(left);
      } else {
        curr1.assign(curr1.begin() + m, curr1.end());
      }
    }
    ll a = curr1[0];
    vector<ll> curr2 = S2;
    while (curr2.size() > 1) {
      int m = curr2.size() / 2;
      vector<ll> left(curr2.begin(), curr2.begin() + m);
      vector<ll> testt = {a};
      testt.insert(testt.end(), left.begin(), left.end());
      ll cl = queryy(testt);
      if (cl >= 1) {
        curr2 = std::move(left);
      } else {
        curr2.assign(curr2.begin() + m, curr2.end());
      }
    }
    ll b = curr2[0];
    return {a, b};
  }
}

bool verif(ll m, double nestt) {
  if (m < 2 || m > 1000000000LL) return false;
  vector<ll> z;
  set<ll> us;
  while ((int)z.size() < 20) {
    ll x = (rng() % MODD) + 1;
    if (us.find(x) == us.end()) {
      us.insert(x);
      z.push_back(x);
    }
  }
  unordered_map<ll, int> freq;
  for (ll val : z) {
    ll r = ((val % m) + m) % m;
    freq[r]++;
  }
  ll sim = 0;
  for (auto& p : freq) {
    int s = p.second;
    sim += 1LL * s * (s - 1) / 2;
  }
  ll act = queryy(z);
  return act == sim;
}

vector<ll> get_possible(ll g, double nestt) {
  vector<pair<double, ll>> cands;
  for (ll f = 1; f <= 10000; ++f) {
    if (g % f == 0) {
      ll cand = g / f;
      if (cand >= 2 && cand <= 1000000000LL) {
        double dist = abs((double)cand - nestt);
        cands.emplace_back(dist, cand);
      }
    }
  }
  sort(cands.begin(), cands.end());
  vector<ll> poss;
  for (auto& pr : cands) {
    poss.push_back(pr.second);
  }
  return poss;
}

int main() {
  vector<ll> ds;
  double nestt = 0;
  ll binomk = (ll)KK * (KK - 1) / 2;
  for (int att = 0; att < 3; ++att) {  // up to 3
    vector<ll> S;
    set<ll> us;
    while ((int)S.size() < KK) {
      ll x = (rng() % MODD) + 1;
      if (us.find(x) == us.end()) {
        us.insert(x);
        S.push_back(x);
      }
    }
    ll c = queryy(S);
    int tr = 0;
    while (c < 1 && tr < 100) {
      ++tr;
      us.clear();
      S.clear();
      while ((int)S.size() < KK) {
        ll x = (rng() % MODD) + 1;
        if (us.find(x) == us.end()) {
          us.insert(x);
          S.push_back(x);
        }
      }
      c = queryy(S);
    }
    if (c < 1) {
      // fallback, but shouldn't happen
      continue;
    }
    if (att == 0) {
      nestt = binomk * 1.0 / c;
    }
    auto pr = find_coll(S);
    ll d = abs(pr.first - pr.second);
    ds.push_back(d);
    if (ds.size() == 2) break;
  }
  ll g = (ds.size() >= 1 ? ds[0] : 2LL);
  for (size_t i = 1; i < ds.size(); ++i) {
    g = __gcd(g, ds[i]);
  }
  vector<ll> poss = get_possible(g, nestt);
  for (ll cand : poss) {
    if (verif(cand, nestt)) {
      cout << 1 << " " << cand << endl;
      cout.flush();
      return 0;
    }
  }
  // if not, try with more if ds.size()<3
  if (ds.size() < 3) {
    // do the third if not already
    // but for simplicity, since in loop up to 3, but code above does up to 3 ds
    // wait, the loop is for att<3, so ds up to 3
    // then g is gcd of up to 3
    // so already done
  }
  // fallback
  ll best_cand = 2;
  if (!poss.empty()) {
    best_cand = poss[0];
  }
  cout << 1 << " " << best_cand << endl;
  cout.flush();
  return 0;
}