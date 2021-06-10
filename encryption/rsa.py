import random
import math


def is_prime(n):
    if n <= 3:
      return n > 1
    if n % 2 == 0 or n % 3 == 0:
      return False
    i = 5
    while i ** 2 <= n:
      if n % i == 0 or n % (i + 2) == 0:
          return False
      i += 6
    return True

def get_prime(size):
  p = 0
  while not is_prime(p):
    p = random.randint(size, size*10)
  return p

def get_gcd(a, b):
  if b:
    return get_gcd(b, a % b)
  else:
    return a

def get_lcm(a, b):
  lcm = abs(a*b) // get_gcd(a, b)
  return lcm

def get_keys(prime_size, e=65537):
  p = get_prime(size=prime_size)
  q = get_prime(size=1000*prime_size)
  lambda_n = get_lcm(p-1, q-1)
  d = pow(e, -1, lambda_n)
  assert (1 < e < lambda_n) and (get_gcd(e, lambda_n) == 1)
  public_key = {'n': p*q, 'e': e}
  private_key = {'n': p*q, 'd': d}
  return private_key, public_key

def secure_fast_mod_exp(base, power, mod):
  result = 1
  while power > 0:
    sBit = (power % 2) == 1        
    result = ((result*base) % mod)*sBit + (1-sBit)*result
    power = power // 2
    base = (base * base) % mod
  return result

def message_to_integer(message, conv_dict):
  integer_message = ''
  for l in message:
    integer_message += conv_dict[l]
  return integer_message

def integer_to_message(integer_message, conv_dict):
  message = ''
  temp_message = str(integer_message)
  for i in range(0, len(temp_message), 3):
    message += conv_dict.get(temp_message[i:i+3], '?')
  return message

def split_message(message, prime_size):
  splits = []
  k = 3*int((prime_size - 1)/3)
  for i in range(0, len(message), k):
    splits.append(message[i:i+k])
  return splits

def encrypt_message(message, public_key, conv_dict):
  message = message_to_integer(message, conv_dict['forward'])
  encrypted_message = []
  for split in split_message(message, len(str(public_key['n']))): 
    encrypted_split = secure_fast_mod_exp(int(split), 
                                          public_key['e'],
                                          public_key['n'])
    encrypted_message.append(encrypted_split)
  return encrypted_message

def decrypt_message(encrypted_splits, private_key, conv_dict_rev):
  decrypted_message = ''
  for encrypted_split in encrypted_splits:
    decrypted_split = secure_fast_mod_exp(encrypted_split, 
                                          private_key['d'],
                                          private_key['n'])
    decrypted_message += integer_to_message(decrypted_split, conv_dict['backward']) 
  return decrypted_message


if __name__ == '__main__':
  import argparse
  from utils import get_conv_dict
  
  parser = argparse.ArgumentParser(description='rsa enctyption')
  parser.add_argument('--message', type=str, default='Hello there!')
  args = parser.parse_args()

  private_key, public_key = get_keys(prime_size=10**10, e=65537)

  conv_dict = get_conv_dict()
  message = args.message

  message = 'The idea of an asymmetric public-private key cryptosystem is attributed to Whitfield Diffie and Martin Hellman, who published this concept in 1976. They also introduced digital signatures and attempted to apply number theory. Their formulation used a shared-secret-key created from exponentiation of some number, modulo a prime number. However, they left open the problem of realizing a one-way function, possibly because the difficulty of factoring was not well-studied at the time.'

  print("\noriginal: {}\n".format(message))
  encrypted_message = encrypt_message(message, public_key, conv_dict)
  print("encrypted: {}\n".format(encrypted_message))
  decrypted_message = decrypt_message(encrypted_message, private_key, conv_dict)
  print("decrypted: {}".format(decrypted_message))












    





