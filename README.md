## minecart

Opinionated [fpm](https://github.com/jordansissel/fpm) wrapper.

Generate deb files from ruby web apps while keeping capistrano compatible directory hierarchy.


### usage

```bash
./minecart.py <manifest>
```

#### example manisfest

```json
{
	"name": "myapp",
	"maintainer": "email@example.com",
	"vendor": "someone",
	"url": "https://github.com/jacoelho/myapp",
	"install_directory": "/var/www/",
	"user": "rails",
	"configuration_files": [
		"config/application.yml",
		"config/database.yml"
	],
	"install_deps": [],
	"build_deps": ["libpq-dev"],
	"instructions": [
		"git clone --depth=1 https://${GITHUB_TOKEN}:x-oauth-basic@github.com/jacoelho/myapp.git .",
		"rm -fr .git/",
		"bundle install --deployment --without development:test"
	]
}
```

this package will be installed in ```/var/www/myapp/releases/<date>``` and symlink to ```/var/www/myapp/current```

the current ruby and bundler will be added to the package install dependencies.

shell env is available during build.

### dependencies

python3 installed

### faq

#### why json
it is on python standard library
